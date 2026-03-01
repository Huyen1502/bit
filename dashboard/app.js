const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const pct = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const formatPct = (value) => `${pct.format(value)}%`;
const formatYears = (value) => `${pct.format(value)}y`;
const formatDate = (value) => new Date(value).toISOString().slice(0, 10);

function parseCsv(path) {
  return new Promise((resolve, reject) => {
    Papa.parse(path, {
      download: true,
      header: true,
      dynamicTyping: true,
      skipEmptyLines: true,
      complete: ({ data }) => resolve(data),
      error: reject,
    });
  });
}

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

function renderTableRows(tableId, rowsHtml) {
  document.querySelector(`#${tableId} tbody`).innerHTML = rowsHtml;
}

function buildPriceChart(daily) {
  const chart = echarts.init(document.getElementById("priceChart"));
  chart.setOption({
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    legend: { top: 0, textStyle: { color: "#62707d" } },
    grid: { left: 60, right: 30, top: 52, bottom: 45 },
    xAxis: {
      type: "category",
      data: daily.map((d) => d.date),
      axisLabel: { color: "#62707d", hideOverlap: true },
      axisLine: { lineStyle: { color: "rgba(31,42,55,0.12)" } },
    },
    yAxis: {
      type: "value",
      scale: true,
      axisLabel: { color: "#62707d", formatter: (v) => `$${Math.round(v / 1000)}k` },
      splitLine: { lineStyle: { color: "rgba(31,42,55,0.08)" } },
    },
    series: [
      {
        name: "Close",
        type: "line",
        smooth: true,
        showSymbol: false,
        data: daily.map((d) => d.Close),
        lineStyle: { width: 3, color: "#223a5e" },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(34,58,94,0.28)" },
            { offset: 1, color: "rgba(34,58,94,0.02)" },
          ]),
        },
      },
      {
        name: "ATH Close",
        type: "line",
        smooth: true,
        showSymbol: false,
        data: daily.map((d) => d.ath_close),
        lineStyle: { width: 2, color: "#c7972b", type: "dashed" },
      },
    ],
  });
  return chart;
}

function buildDrawdownChart(daily) {
  const chart = echarts.init(document.getElementById("drawdownChart"));
  chart.setOption({
    tooltip: { trigger: "axis", valueFormatter: (v) => formatPct(v) },
    grid: { left: 55, right: 20, top: 22, bottom: 40 },
    xAxis: {
      type: "category",
      data: daily.map((d) => d.date),
      axisLabel: { color: "#62707d", hideOverlap: true },
      axisLine: { lineStyle: { color: "rgba(31,42,55,0.12)" } },
    },
    yAxis: {
      type: "value",
      max: 0,
      axisLabel: { color: "#62707d", formatter: (v) => `${v}%` },
      splitLine: { lineStyle: { color: "rgba(31,42,55,0.08)" } },
    },
    series: [
      {
        type: "line",
        smooth: true,
        showSymbol: false,
        data: daily.map((d) => d.drawdown_pct),
        lineStyle: { width: 2, color: "#b64633" },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(182,70,51,0.35)" },
            { offset: 1, color: "rgba(182,70,51,0.02)" },
          ]),
        },
      },
    ],
  });
  return chart;
}

function buildMonthlyReturnChart(monthly) {
  const chart = echarts.init(document.getElementById("monthlyReturnChart"));
  chart.setOption({
    tooltip: { trigger: "axis", valueFormatter: (v) => formatPct(v) },
    grid: { left: 55, right: 20, top: 22, bottom: 52 },
    xAxis: {
      type: "category",
      data: monthly.map((d) => d.year_month),
      axisLabel: { color: "#62707d", rotate: 45 },
      axisLine: { lineStyle: { color: "rgba(31,42,55,0.12)" } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#62707d", formatter: (v) => `${v}%` },
      splitLine: { lineStyle: { color: "rgba(31,42,55,0.08)" } },
    },
    series: [
      {
        type: "bar",
        data: monthly.map((d) => ({
          value: d.monthly_return_pct,
          itemStyle: { color: d.monthly_return_pct >= 0 ? "#1b7f5b" : "#b64633" },
        })),
        barMaxWidth: 18,
      },
    ],
  });
  return chart;
}

function buildRegimeChart(regimes) {
  const chart = echarts.init(document.getElementById("regimeChart"));
  chart.setOption({
    tooltip: {
      trigger: "item",
      formatter: (p) => {
        const item = p.data.meta;
        return [
          `<strong>${item.regime.toUpperCase()}</strong>`,
          `Start: ${item.start_date}`,
          `End: ${item.end_date}`,
          `Duration: ${formatYears(item.duration_years)}`,
          `Return: ${formatPct(item.segment_return_pct)}`,
          `Min DD: ${formatPct(item.min_drawdown_pct)}`,
        ].join("<br>");
      },
    },
    grid: { left: 30, right: 30, top: 20, bottom: 20, containLabel: true },
    xAxis: { type: "value", show: false },
    yAxis: {
      type: "category",
      data: regimes.map((r) => `${r.start_year_month} -> ${r.end_year_month}`),
      axisLabel: { color: "#62707d" },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        type: "bar",
        data: regimes.map((r) => ({
          value: r.duration_years,
          itemStyle: { color: r.regime === "bull" ? "#1b7f5b" : "#b64633", borderRadius: 10 },
          meta: r,
        })),
        barWidth: 24,
      },
    ],
  });
  return chart;
}

function buildCycleChart(cycles) {
  const chart = echarts.init(document.getElementById("cycleChart"));
  chart.setOption({
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
    },
    legend: { top: 0, textStyle: { color: "#62707d" } },
    grid: { left: 55, right: 40, top: 50, bottom: 40 },
    xAxis: {
      type: "category",
      data: cycles.map((c) => `Cycle ${c.cycle_no}`),
      axisLabel: { color: "#62707d" },
      axisLine: { lineStyle: { color: "rgba(31,42,55,0.12)" } },
    },
    yAxis: [
      {
        type: "value",
        name: "Years",
        axisLabel: { color: "#62707d" },
        splitLine: { lineStyle: { color: "rgba(31,42,55,0.08)" } },
      },
      {
        type: "value",
        name: "Return %",
        axisLabel: { color: "#62707d", formatter: (v) => `${Math.round(v)}%` },
      },
    ],
    series: [
      {
        name: "Cycle Years",
        type: "bar",
        yAxisIndex: 0,
        data: cycles.map((c) => c.cycle_duration_years),
        itemStyle: { color: "#223a5e", borderRadius: [8, 8, 0, 0] },
        barMaxWidth: 36,
      },
      {
        name: "Cycle Return %",
        type: "line",
        yAxisIndex: 1,
        smooth: true,
        data: cycles.map((c) => c.cycle_return_pct),
        lineStyle: { width: 3, color: "#c7972b" },
        itemStyle: { color: "#c7972b" },
      },
    ],
  });
  return chart;
}

function renderRegimeTable(regimes) {
  const html = regimes
    .slice()
    .reverse()
    .map((r) => `
      <tr>
        <td><span class="tag ${r.regime}">${r.regime}</span></td>
        <td>${r.start_date}</td>
        <td>${r.end_date}</td>
        <td>${formatYears(r.duration_years)}</td>
        <td class="${r.segment_return_pct >= 0 ? "pos" : "neg"}">${formatPct(r.segment_return_pct)}</td>
        <td class="neg">${formatPct(r.min_drawdown_pct)}</td>
      </tr>
    `)
    .join("");
  renderTableRows("regimeTable", html);
}

function renderCycleTable(cycles) {
  const html = cycles
    .slice()
    .reverse()
    .map((c) => `
      <tr>
        <td>${c.cycle_no}</td>
        <td>${c.bull_start}</td>
        <td>${c.bear_end}</td>
        <td>${formatYears(c.cycle_duration_years)}</td>
        <td class="${c.bull_return_pct >= 0 ? "pos" : "neg"}">${formatPct(c.bull_return_pct)}</td>
        <td class="${c.bear_return_pct >= 0 ? "pos" : "neg"}">${formatPct(c.bear_return_pct)}</td>
        <td class="${c.cycle_return_pct >= 0 ? "pos" : "neg"}">${formatPct(c.cycle_return_pct)}</td>
      </tr>
    `)
    .join("");
  renderTableRows("cycleTable", html);
}

function updateKpis(daily, monthly, cycles) {
  const latestDaily = daily[daily.length - 1];
  const latestMonthly = monthly[monthly.length - 1];
  const avgCycleYears =
    cycles.reduce((sum, cycle) => sum + cycle.cycle_duration_years, 0) / cycles.length;
  const maxDrawdown = Math.min(...daily.map((d) => d.drawdown_pct));

  setText("latestDate", `Latest data: ${formatDate(latestDaily.date)}`);
  setText("latestRegime", latestMonthly.regime.toUpperCase());
  setText("kpiClose", currency.format(latestDaily.Close));
  setText("kpiAth", currency.format(latestDaily.ath_close));
  setText("kpiDrawdown", formatPct(latestDaily.drawdown_pct));
  setText("kpiMaxDd", formatPct(maxDrawdown));
  setText("kpiCycleYears", formatYears(avgCycleYears));
  setText("kpiMonthlyRegime", latestMonthly.regime.toUpperCase());
}

async function bootstrap() {
  const [daily, monthly, regimes, cycles] = await Promise.all([
    parseCsv("./data/btc_daily.csv"),
    parseCsv("./data/btc_monthly.csv"),
    parseCsv("./data/btc_monthly_regimes.csv"),
    parseCsv("./data/btc_monthly_cycles.csv"),
  ]);

  updateKpis(daily, monthly, cycles);
  renderRegimeTable(regimes);
  renderCycleTable(cycles);

  const charts = [
    buildPriceChart(daily),
    buildDrawdownChart(daily),
    buildMonthlyReturnChart(monthly),
    buildRegimeChart(regimes),
    buildCycleChart(cycles),
  ];

  window.addEventListener("resize", () => charts.forEach((chart) => chart.resize()));
}

bootstrap().catch((error) => {
  console.error(error);
  document.body.insertAdjacentHTML(
    "beforeend",
    `<p style="padding:16px;color:#b64633">Failed to load dashboard data.</p>`
  );
});
