from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


INPUT_CSV = Path("btc_daily.csv")
OUTPUT_DIR = Path("output/spreadsheet")
PBI_OUTPUT_DIR = OUTPUT_DIR / "powerbi"
WEB_DATA_DIR = Path("dashboard/data")
BEAR_DRAWDOWN_THRESHOLD = -20.0  # % so với đỉnh gần nhất (ATH-based drawdown)


def load_btc_daily(csv_path: Path) -> pd.DataFrame:
    """Đọc file BTC daily (hỗ trợ định dạng Yahoo Finance multi-row header)."""
    preview = pd.read_csv(csv_path, nrows=4, header=None)

    if (
        preview.shape[0] >= 3
        and str(preview.iloc[0, 0]).strip() == "Price"
        and str(preview.iloc[2, 0]).strip() == "Date"
    ):
        df = pd.read_csv(
            csv_path,
            skiprows=3,
            names=["Date", "Close", "High", "Low", "Open", "Volume"],
        )
    else:
        df = pd.read_csv(csv_path)
        rename_map = {c: str(c).strip().title() for c in df.columns}
        df = df.rename(columns=rename_map)
        if "Date" not in df.columns:
            raise ValueError("Không tìm thấy cột Date trong btc_daily.csv")

    for col in ["Close", "High", "Low", "Open", "Volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date", "Close"]).sort_values("Date").reset_index(drop=True)

    return df


def add_daily_metrics(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["daily_return_pct"] = out["Close"].pct_change() * 100
    out["ath_close"] = out["Close"].cummax()
    out["drawdown_pct"] = (out["Close"] / out["ath_close"] - 1.0) * 100
    out["is_bear"] = out["drawdown_pct"] <= BEAR_DRAWDOWN_THRESHOLD
    out["regime"] = np.where(out["is_bear"], "bear", "bull")
    return out


def build_monthly_returns(df_daily: pd.DataFrame) -> pd.DataFrame:
    # pandas mới dùng "ME" (month-end), pandas cũ thường dùng "M".
    month_end_freq = "ME"
    monthly = (
        df_daily.set_index("Date")[["Close"]]
        .resample(month_end_freq)
        .last()
        .dropna()
        .rename(columns={"Close": "month_end_close"})
    )
    monthly["monthly_return_pct"] = monthly["month_end_close"].pct_change() * 100
    monthly["year"] = monthly.index.year
    monthly["month"] = monthly.index.month
    monthly = monthly.reset_index().rename(columns={"Date": "month_end"})
    return monthly


def build_regime_segments(df_daily: pd.DataFrame) -> pd.DataFrame:
    tmp = df_daily.copy()
    tmp["segment_id"] = (tmp["regime"] != tmp["regime"].shift(1)).cumsum()

    segments = (
        tmp.groupby("segment_id", as_index=False)
        .agg(
            regime=("regime", "first"),
            start_date=("Date", "first"),
            end_date=("Date", "last"),
            start_close=("Close", "first"),
            end_close=("Close", "last"),
            min_close=("Close", "min"),
            max_close=("Close", "max"),
            min_drawdown_pct=("drawdown_pct", "min"),
            max_drawdown_pct=("drawdown_pct", "max"),
            n_days=("Date", "size"),
        )
        .copy()
    )

    segments["segment_return_pct"] = (
        (segments["end_close"] / segments["start_close"]) - 1.0
    ) * 100
    segments["duration_days"] = (
        segments["end_date"] - segments["start_date"]
    ).dt.days + 1
    segments["duration_years"] = segments["duration_days"] / 365.25
    return segments


def build_bull_bear_cycles(segments: pd.DataFrame) -> pd.DataFrame:
    """Chu kỳ = 1 giai đoạn bull liền sau bởi 1 giai đoạn bear."""
    rows = []
    segments = segments.reset_index(drop=True)

    for i in range(len(segments) - 1):
        s1 = segments.iloc[i]
        s2 = segments.iloc[i + 1]
        if s1["regime"] != "bull" or s2["regime"] != "bear":
            continue

        cycle_days = (s2["end_date"] - s1["start_date"]).days + 1
        rows.append(
            {
                "cycle_no": len(rows) + 1,
                "bull_start": s1["start_date"],
                "bull_end": s1["end_date"],
                "bear_start": s2["start_date"],
                "bear_end": s2["end_date"],
                "bull_duration_days": int(s1["duration_days"]),
                "bear_duration_days": int(s2["duration_days"]),
                "cycle_duration_days": int(cycle_days),
                "bull_duration_years": s1["duration_days"] / 365.25,
                "bear_duration_years": s2["duration_days"] / 365.25,
                "cycle_duration_years": cycle_days / 365.25,
                "bull_return_pct": s1["segment_return_pct"],
                "bear_return_pct": s2["segment_return_pct"],
                "cycle_return_pct": ((s2["end_close"] / s1["start_close"]) - 1.0) * 100,
            }
        )

    return pd.DataFrame(rows)


def build_dim_date(df_daily: pd.DataFrame) -> pd.DataFrame:
    dim = pd.DataFrame({"date": pd.to_datetime(df_daily["Date"]).drop_duplicates().sort_values()})
    dim["year"] = dim["date"].dt.year
    dim["quarter"] = "Q" + dim["date"].dt.quarter.astype(str)
    dim["month"] = dim["date"].dt.month
    dim["month_name"] = dim["date"].dt.strftime("%b")
    dim["year_month"] = dim["date"].dt.strftime("%Y-%m")
    dim["month_start"] = dim["date"].dt.to_period("M").dt.start_time
    dim["month_end"] = dim["date"].dt.to_period("M").dt.end_time.dt.normalize()
    dim["week_of_year"] = dim["date"].dt.isocalendar().week.astype(int)
    return dim


def prepare_powerbi_daily(daily: pd.DataFrame) -> pd.DataFrame:
    out = daily.copy()
    out = out.rename(columns={"Date": "date"})
    out["is_bear_flag"] = out["is_bear"].astype(int)
    out["year"] = out["date"].dt.year
    out["month"] = out["date"].dt.month
    out["year_month"] = out["date"].dt.strftime("%Y-%m")
    out["month_end"] = out["date"].dt.to_period("M").dt.end_time.dt.normalize()
    out = out.drop(columns=["is_bear"])
    return out


def prepare_powerbi_monthly(monthly: pd.DataFrame) -> pd.DataFrame:
    out = monthly.copy()
    out["year_month"] = pd.to_datetime(out["month_end"]).dt.strftime("%Y-%m")
    out["month_name"] = pd.to_datetime(out["month_end"]).dt.strftime("%b")
    return out


def prepare_powerbi_regimes(regimes: pd.DataFrame, frequency: str) -> pd.DataFrame:
    out = regimes.copy()
    out["frequency"] = frequency
    out["regime_id"] = [f"{frequency}_{i}" for i in range(1, len(out) + 1)]
    out = out.rename(columns={"n_days": "observation_count"})
    out["start_year_month"] = pd.to_datetime(out["start_date"]).dt.strftime("%Y-%m")
    out["end_year_month"] = pd.to_datetime(out["end_date"]).dt.strftime("%Y-%m")
    cols = [
        "regime_id",
        "segment_id",
        "frequency",
        "regime",
        "start_date",
        "end_date",
        "start_year_month",
        "end_year_month",
        "start_close",
        "end_close",
        "min_close",
        "max_close",
        "min_drawdown_pct",
        "max_drawdown_pct",
        "observation_count",
        "duration_days",
        "duration_years",
        "segment_return_pct",
    ]
    return out[cols]


def prepare_powerbi_cycles(cycles: pd.DataFrame, frequency: str) -> pd.DataFrame:
    out = cycles.copy()
    out["frequency"] = frequency
    out["cycle_id"] = [f"{frequency}_{i}" for i in out["cycle_no"]]
    out["bull_start_year_month"] = pd.to_datetime(out["bull_start"]).dt.strftime("%Y-%m")
    out["bull_end_year_month"] = pd.to_datetime(out["bull_end"]).dt.strftime("%Y-%m")
    out["bear_start_year_month"] = pd.to_datetime(out["bear_start"]).dt.strftime("%Y-%m")
    out["bear_end_year_month"] = pd.to_datetime(out["bear_end"]).dt.strftime("%Y-%m")
    cols = [
        "cycle_id",
        "cycle_no",
        "frequency",
        "bull_start",
        "bull_end",
        "bear_start",
        "bear_end",
        "bull_start_year_month",
        "bull_end_year_month",
        "bear_start_year_month",
        "bear_end_year_month",
        "bull_duration_days",
        "bear_duration_days",
        "cycle_duration_days",
        "bull_duration_years",
        "bear_duration_years",
        "cycle_duration_years",
        "bull_return_pct",
        "bear_return_pct",
        "cycle_return_pct",
    ]
    return out[cols]


def write_powerbi_exports(
    daily: pd.DataFrame,
    monthly: pd.DataFrame,
    regimes: pd.DataFrame,
    monthly_regimes: pd.DataFrame,
    cycles: pd.DataFrame,
    monthly_cycles: pd.DataFrame,
) -> None:
    PBI_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dim_date = build_dim_date(daily)
    pbi_daily = prepare_powerbi_daily(daily)
    pbi_monthly = prepare_powerbi_monthly(monthly)
    pbi_regimes_daily = prepare_powerbi_regimes(regimes, "daily")
    pbi_regimes_monthly = prepare_powerbi_regimes(monthly_regimes, "monthly")
    pbi_cycles_daily = prepare_powerbi_cycles(cycles, "daily")
    pbi_cycles_monthly = prepare_powerbi_cycles(monthly_cycles, "monthly")

    dim_date.to_csv(PBI_OUTPUT_DIR / "dim_date.csv", index=False)
    pbi_daily.to_csv(PBI_OUTPUT_DIR / "fact_btc_daily.csv", index=False)
    pbi_monthly.to_csv(PBI_OUTPUT_DIR / "fact_btc_monthly.csv", index=False)
    pbi_regimes_daily.to_csv(PBI_OUTPUT_DIR / "fact_btc_regimes_daily.csv", index=False)
    pbi_regimes_monthly.to_csv(PBI_OUTPUT_DIR / "fact_btc_regimes_monthly.csv", index=False)
    pbi_cycles_daily.to_csv(PBI_OUTPUT_DIR / "fact_btc_cycles_daily.csv", index=False)
    pbi_cycles_monthly.to_csv(PBI_OUTPUT_DIR / "fact_btc_cycles_monthly.csv", index=False)


def write_dashboard_exports(
    daily: pd.DataFrame,
    monthly: pd.DataFrame,
    monthly_regimes: pd.DataFrame,
    monthly_cycles: pd.DataFrame,
) -> None:
    WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)

    web_daily = daily.rename(columns={"Date": "date"}).copy()
    web_daily["is_bear_flag"] = web_daily["is_bear"].astype(int)
    web_daily["month_end"] = web_daily["date"].dt.to_period("M").dt.end_time.dt.normalize()
    web_daily = web_daily.drop(columns=["is_bear"])

    web_monthly = monthly.copy()
    web_monthly["year_month"] = pd.to_datetime(web_monthly["month_end"]).dt.strftime("%Y-%m")

    web_regimes = monthly_regimes.copy()
    web_regimes = web_regimes.rename(columns={"n_days": "observation_count"})
    web_regimes["start_year_month"] = pd.to_datetime(web_regimes["start_date"]).dt.strftime("%Y-%m")
    web_regimes["end_year_month"] = pd.to_datetime(web_regimes["end_date"]).dt.strftime("%Y-%m")

    web_cycles = monthly_cycles.copy()
    web_cycles["bull_start_year_month"] = pd.to_datetime(web_cycles["bull_start"]).dt.strftime("%Y-%m")
    web_cycles["bear_end_year_month"] = pd.to_datetime(web_cycles["bear_end"]).dt.strftime("%Y-%m")

    web_daily.to_csv(WEB_DATA_DIR / "btc_daily.csv", index=False)
    web_monthly.to_csv(WEB_DATA_DIR / "btc_monthly.csv", index=False)
    web_regimes.to_csv(WEB_DATA_DIR / "btc_monthly_regimes.csv", index=False)
    web_cycles.to_csv(WEB_DATA_DIR / "btc_monthly_cycles.csv", index=False)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PBI_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)

    df = load_btc_daily(INPUT_CSV)
    daily = add_daily_metrics(df)
    monthly = build_monthly_returns(daily)
    monthly_regime_base = monthly.rename(
        columns={"month_end": "Date", "month_end_close": "Close"}
    ).copy()
    monthly_regime_base = add_daily_metrics(monthly_regime_base)
    monthly = (
        monthly.merge(
            monthly_regime_base[["Date", "ath_close", "drawdown_pct", "regime"]],
            left_on="month_end",
            right_on="Date",
            how="left",
        )
        .drop(columns=["Date"])
    )
    monthly = monthly[
        [
            "month_end",
            "month_end_close",
            "ath_close",
            "drawdown_pct",
            "monthly_return_pct",
            "regime",
            "year",
            "month",
        ]
    ]
    regimes = build_regime_segments(daily)
    cycles = build_bull_bear_cycles(regimes)
    monthly_regimes = build_regime_segments(monthly_regime_base)
    monthly_cycles = build_bull_bear_cycles(monthly_regimes)

    daily_out = OUTPUT_DIR / "btc_daily_metrics.csv"
    monthly_out = OUTPUT_DIR / "btc_monthly_returns.csv"
    regime_out = OUTPUT_DIR / "btc_market_regimes.csv"
    cycle_out = OUTPUT_DIR / "btc_bull_bear_cycles.csv"
    monthly_regime_out = OUTPUT_DIR / "btc_monthly_market_regimes.csv"
    monthly_cycle_out = OUTPUT_DIR / "btc_monthly_bull_bear_cycles.csv"

    daily.to_csv(daily_out, index=False)
    monthly.to_csv(monthly_out, index=False)
    regimes.to_csv(regime_out, index=False)
    cycles.to_csv(cycle_out, index=False)
    monthly_regimes.to_csv(monthly_regime_out, index=False)
    monthly_cycles.to_csv(monthly_cycle_out, index=False)
    write_powerbi_exports(daily, monthly, regimes, monthly_regimes, cycles, monthly_cycles)
    write_dashboard_exports(daily, monthly, monthly_regimes, monthly_cycles)

    print("=== BTC Market Analysis (ATH drawdown threshold = -20%) ===")
    print(f"Data range: {daily['Date'].min().date()} -> {daily['Date'].max().date()} ({len(daily):,} rows)")
    print("")
    print("1) Daily returns + drawdown:")
    print(f"   - File: {daily_out}")
    print(f"   - Max drawdown: {daily['drawdown_pct'].min():.2f}%")
    print("")
    print("2) Monthly returns:")
    print(f"   - File: {monthly_out}")
    print(f"   - Months: {len(monthly):,}")
    print("")
    print("3) Bull/Bear regimes (bear when drawdown <= -20%):")
    print(f"   - File: {regime_out}")
    print(f"   - Bear segments: {(regimes['regime'] == 'bear').sum()}")
    print(f"   - Bull segments: {(regimes['regime'] == 'bull').sum()}")
    print(regimes[["regime", "start_date", "end_date", "duration_days", "segment_return_pct", "min_drawdown_pct"]].tail(10).to_string(index=False))
    print("")
    print("4) Bull->Bear cycles duration:")
    print(f"   - File: {cycle_out}")
    if not cycles.empty:
        print(f"   - Avg cycle duration: {cycles['cycle_duration_years'].mean():.2f} years")
        print(f"   - Median cycle duration: {cycles['cycle_duration_years'].median():.2f} years")
        print(cycles.tail(10).to_string(index=False))
    else:
        print("   - No complete bull->bear cycles found by current rule.")

    print("")
    print("Macro view (monthly, clearer for chu ky thi truong):")
    print(f"   - Monthly regimes file: {monthly_regime_out}")
    print(f"   - Monthly cycles file: {monthly_cycle_out}")
    print(monthly_regimes[["regime", "start_date", "end_date", "duration_days", "duration_years", "segment_return_pct", "min_drawdown_pct"]].to_string(index=False))
    if not monthly_cycles.empty:
        print("")
        print(f"   - Avg monthly-cycle duration: {monthly_cycles['cycle_duration_years'].mean():.2f} years")
        print(f"   - Median monthly-cycle duration: {monthly_cycles['cycle_duration_years'].median():.2f} years")
        print(monthly_cycles.to_string(index=False))
    print("")
    print("Power BI ready exports:")
    print(f"   - Folder: {PBI_OUTPUT_DIR}")
    print("Dashboard data exports:")
    print(f"   - Folder: {WEB_DATA_DIR}")


if __name__ == "__main__":
    main()
