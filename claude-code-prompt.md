# Prompt for Claude Code — upgrade "Finance Insight" project

Copy everything below into Claude Code in VS Code, with `finance-insight-demo.html` placed in the repo root as the design reference.

---

I'm upgrading my personal finance website ("Finance Insight" — brand always capitalized exactly like that) from a data-storage site into a stock-market analysis and news platform. This is an educational project for building my own analysis skills — it must never present itself as investment advice, and it never touches real money.

**Design reference:** `finance-insight-demo.html` in the repo root is an approved, working single-file demo of the exact look, layout, interactions, and copy tone I want. Open it, study it, and replicate its design system faithfully. The style is professional and Yahoo-Finance-clean: white background, near-black typography, thin gray dividers, small 3–4px corner radii (nothing pill-shaped or bubbly), Helvetica/system sans for UI + IBM Plex Mono for numbers (tabular-nums). Color is strictly rationed: blue (#0f69ff) only for links, active states, and primary buttons; green/red reserved exclusively for price changes and semantic P&L; everything non-emphasized stays black/gray. Colors are defined in OKLCH with hex fallbacks — keep that. Do not reintroduce dark themes, green accents, heavy rounding, or decorative color.

## Architecture

- Multi-page app with client-side routing — each nav tab is its own page (Dashboard, Watchlist, Sectors, Analysis, Daily brief, Journal), exactly like the demo's hash router. Pick the stack you think fits best (Next.js or Flask+templates are both fine — ask me before scaffolding), but preserve the one-page-per-tab structure.
- Backend with a database (SQLite is fine to start) storing: daily OHLCV per ticker, computed indicators, news items with ticker/sector tags and sentiment, my journal entries, scorecards, and the agent's paper trades. My existing stored data should migrate into this schema.
- A scheduled job (cron or equivalent) that runs daily after market close: fetch prices (yfinance), compute indicators, fetch news, run sentiment, generate the morning brief.

## Pages & features (all mocked in the demo — make them real)

1. **Dashboard** — hero with live index chart (1D/1W/1M/1Y), scrolling market tape, links into other pages.
2. **Watchlist** — table with 30-session sparkline, price, 1D/1M change, RSI(14), aggregated news sentiment per ticker, and a "Trade ↗" button opening a menu of outbound deep links (Robinhood, Yahoo Finance, TradingView — links only, with the "convenience, not endorsement" note; no affiliate links).
3. **Sectors** — 11-sector heatmap of 1-month relative performance vs SPY, computed from sector ETF prices (XLK, XLE, SOXX, etc.).
4. **Analysis** (per ticker) — indicator chips (RSI, MACD, 50D/200D), auto-assembled bull case vs bear case, plus:
   - **AI research desk**: on-demand report via Anthropic API — one call per role (Technical, Fundamental, Sentiment, Risk Manager), each prompted with MY computed indicator values and stored news (never let the model invent numbers), then a Portfolio Manager synthesis call producing Rating (Overweight/Neutral/etc.), thesis, and time horizon. Cache reports; regenerate at most daily per ticker. Match the demo's layout including the skeleton loading state.
   - **Quality scorecard**: 6 dimensions (moat, business model, growth runway, balance sheet, management, valuation), 0–3 each. I score manually; an AI suggestion is shown beside each for comparison. Persist my scores.
5. **Daily brief** — auto-generated each morning (one API call summarizing overnight moves, my watchlist, and top headlines), plus sentiment-tagged news list and a macro calendar (CPI, FOMC, earnings dates for my watchlist). **News items must include images**: fetch each article's thumbnail (og:image from the source, or the image URL the news API provides) and render it Yahoo-Finance style beside the headline; use a neutral gray placeholder when no image exists (see the demo's placeholder pattern). Lazy-load images and cache/proxy them so a slow source doesn't block the page.
6. **Journal** — my prediction journal: thesis, logged date, benchmark, horizon, auto-scored result (hit/miss/open) against real prices; accuracy stats. Plus an **agent paper portfolio**: an AI agent with fake cash that proposes and logs simulated trades daily (with its reasoning stored), and a "You vs Agent vs SPY" comparison strip.

## Guardrails

- Persistent footer + per-feature disclaimers: educational project, not investment advice, simulated portfolios.
- No real-money execution anywhere; broker links are plain outbound links.
- API keys in env vars; rate-limit and cache all external calls; the site must still render (with stale data notice) if a data source is down.
- Keep API costs low: desk reports and briefs are cached; nothing calls the LLM on page load.

## Process

Start by showing me the file structure and schema you propose, and ask me the stack question before writing code. Then build in this order: data layer + ingestion → Watchlist + Dashboard → Sectors → Analysis (indicators + bull/bear) → Daily brief → AI desk + scorecard → Journal + agent portfolio. After each phase, run it and show me before moving on.
