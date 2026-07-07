-- Finance Insight schema. Educational project; no real-money data.

CREATE TABLE IF NOT EXISTS ticker (
    symbol                TEXT PRIMARY KEY,
    name                  TEXT NOT NULL,
    sector                TEXT,
    is_watchlist          INTEGER NOT NULL DEFAULT 0,
    added_at              TEXT NOT NULL,
    market_cap            REAL,
    trailing_pe           REAL,
    forward_pe            REAL,
    week52_low            REAL,
    week52_high           REAL,
    avg_volume            INTEGER,
    target_mean_price     REAL,
    recommendation_key    TEXT,
    dividend_yield        REAL,
    fundamentals_updated_at TEXT
);

CREATE TABLE IF NOT EXISTS sector_etf (
    etf_symbol    TEXT PRIMARY KEY,
    sector_name   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ohlcv (
    symbol   TEXT NOT NULL,
    date     TEXT NOT NULL,
    open     REAL NOT NULL,
    high     REAL NOT NULL,
    low      REAL NOT NULL,
    close    REAL NOT NULL,
    volume   INTEGER NOT NULL,
    PRIMARY KEY (symbol, date)
);
CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_date ON ohlcv(symbol, date);

CREATE TABLE IF NOT EXISTS indicator (
    symbol        TEXT NOT NULL,
    date          TEXT NOT NULL,
    rsi14         REAL,
    macd          REAL,
    macd_signal   REAL,
    sma50         REAL,
    sma200        REAL,
    PRIMARY KEY (symbol, date)
);

CREATE TABLE IF NOT EXISTS news_item (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    url            TEXT NOT NULL UNIQUE,
    title          TEXT NOT NULL,
    source         TEXT,
    published_at   TEXT NOT NULL,
    image_url      TEXT,
    fetched_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS news_tag (
    news_id   INTEGER NOT NULL REFERENCES news_item(id),
    tag       TEXT NOT NULL,
    tag_type  TEXT NOT NULL CHECK (tag_type IN ('ticker', 'sector')),
    PRIMARY KEY (news_id, tag, tag_type)
);
CREATE INDEX IF NOT EXISTS idx_news_tag_tag ON news_tag(tag, tag_type);

CREATE TABLE IF NOT EXISTS news_sentiment (
    news_id    INTEGER PRIMARY KEY REFERENCES news_item(id),
    score      REAL NOT NULL,
    label      TEXT NOT NULL CHECK (label IN ('bullish', 'bearish', 'neutral')),
    scored_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_desk_report (
    ticker          TEXT NOT NULL,
    generated_date  TEXT NOT NULL,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    rating          TEXT,
    horizon         TEXT,
    PRIMARY KEY (ticker, generated_date, role)
);

CREATE TABLE IF NOT EXISTS scorecard (
    ticker      TEXT NOT NULL,
    dimension   TEXT NOT NULL,
    user_score  INTEGER CHECK (user_score BETWEEN 0 AND 3),
    ai_score    INTEGER CHECK (ai_score BETWEEN 0 AND 3),
    updated_at  TEXT NOT NULL,
    PRIMARY KEY (ticker, dimension)
);

CREATE TABLE IF NOT EXISTS journal_entry (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    thesis        TEXT NOT NULL,
    logged_date   TEXT NOT NULL,
    benchmark     TEXT NOT NULL,
    horizon_days  INTEGER NOT NULL,
    direction     TEXT NOT NULL DEFAULT 'up' CHECK (direction IN ('up', 'down')),
    status        TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'hit', 'miss')),
    result_pct    REAL,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_trade (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol      TEXT NOT NULL,
    action      TEXT NOT NULL CHECK (action IN ('buy', 'sell', 'close')),
    trade_date  TEXT NOT NULL,
    size_usd    REAL NOT NULL,
    fill_price  REAL NOT NULL,
    shares      REAL NOT NULL,
    reasoning   TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
    pnl_pct     REAL
);

CREATE TABLE IF NOT EXISTS agent_nav (
    date  TEXT PRIMARY KEY,
    nav   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_brief (
    date            TEXT PRIMARY KEY,
    summary_text    TEXT NOT NULL,
    generated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS macro_event (
    date        TEXT NOT NULL,
    name        TEXT NOT NULL,
    importance  TEXT NOT NULL CHECK (importance IN ('low', 'med', 'high')),
    PRIMARY KEY (date, name)
);

CREATE TABLE IF NOT EXISTS fetch_log (
    source      TEXT NOT NULL,
    fetched_at  TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('ok', 'error')),
    error       TEXT,
    PRIMARY KEY (source, fetched_at)
);
