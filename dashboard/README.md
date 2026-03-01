# BTC Dashboard

Static dashboard for BTC market analysis using:
- `ECharts`
- `Papa Parse`
- CSV data exported from `btc_market_analysis.py`

## Refresh data

Run:

```powershell
py -3 btc_market_analysis.py
```

This updates:

- `dashboard/data/btc_daily.csv`
- `dashboard/data/btc_monthly.csv`
- `dashboard/data/btc_monthly_regimes.csv`
- `dashboard/data/btc_monthly_cycles.csv`

## Local preview

Use any static server. Example with Python:

```powershell
py -3 -m http.server 8000 -d dashboard
```

Open:

`http://localhost:8000`

## Free hosting

### Cloudflare Pages

1. Push this repo to GitHub
2. In Cloudflare Pages, create a new project from that repo
3. Set:
   - Framework preset: `None`
   - Build command: leave empty
   - Build output directory: `dashboard`
4. Deploy

### Vercel

1. Import the GitHub repo
2. Set:
   - Framework preset: `Other`
   - Build command: empty
   - Output directory: `dashboard`
3. Deploy

## Notes

- This dashboard is fully static. No backend required.
- If data changes, rerun `btc_market_analysis.py` and redeploy.
