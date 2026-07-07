const fmt = (x, d = 2) => Number(x).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });

/* ---------- clock ---------- */
(function () {
  const el = document.getElementById('clock');
  if (!el) return;
  function tick() {
    const now = new Date();
    el.textContent = now.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ' · ' +
      now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
  }
  tick();
  setInterval(tick, 1000);
})();

/* ---------- line chart (used by dashboard + analysis) ---------- */
function drawLineChart(svgEl, points) {
  if (!points || points.length === 0) {
    svgEl.innerHTML = '';
    return;
  }
  const closes = points.map((p) => p.c);
  const W = 640, H = 260, P = 6;
  const lo = Math.min(...closes), hi = Math.max(...closes);
  const X = (i) => P + (W - 2 * P) * i / Math.max(points.length - 1, 1);
  const Y = (v) => H - P - (H - 2 * P) * (v - lo) / (hi - lo || 1);
  let d = `M${X(0)},${Y(closes[0])}`;
  closes.forEach((v, i) => { if (i) d += `L${fmt(X(i), 1)},${fmt(Y(v), 1)}`; });
  const up = closes[closes.length - 1] >= closes[0];
  const col = up ? 'var(--up)' : 'var(--down)';
  const grid = [0.25, 0.5, 0.75].map((f) =>
    `<line x1="0" x2="${W}" y1="${H * f}" y2="${H * f}" stroke="var(--border-soft)" stroke-width="1"/>`).join('');
  svgEl.innerHTML = `${grid}
    <path d="${d}L${W - P},${H - P}L${P},${H - P}Z" fill="${col}" opacity="0.08"/>
    <path d="${d}" fill="none" stroke="${col}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
    <circle cx="${X(closes.length - 1)}" cy="${Y(closes[closes.length - 1])}" r="3.5" fill="${col}"/>`;
  return { lo, hi, first: closes[0], last: closes[closes.length - 1], up };
}

/* ---------- trade-out menu ---------- */
(function () {
  const BROKERS = [
    ['Robinhood', (t) => `https://robinhood.com/stocks/${t}`],
    ['Yahoo Finance', (t) => `https://finance.yahoo.com/quote/${t}`],
    ['TradingView', (t) => `https://www.tradingview.com/symbols/${t}/`],
  ];
  const tm = document.createElement('div');
  tm.className = 'trade-menu';
  document.body.appendChild(tm);
  let tmOpenFor = null;

  function openTradeMenu(btn) {
    const t = btn.dataset.ticker;
    tm.innerHTML = BROKERS.map(([n, u]) =>
      `<a href="${u(t)}" target="_blank" rel="noopener noreferrer">${n} · ${t}<span class="ext">↗</span></a>`).join('') +
      `<div class="tm-note">Links for convenience — not an endorsement or investment advice.</div>`;
    const r = btn.getBoundingClientRect();
    tm.classList.add('on');
    const mw = tm.offsetWidth, mh = tm.offsetHeight;
    let x = Math.min(r.right - mw, innerWidth - mw - 8); x = Math.max(8, x);
    let y = r.bottom + 6; if (y + mh > innerHeight - 8) y = r.top - mh - 6;
    tm.style.left = x + 'px'; tm.style.top = y + 'px';
    tmOpenFor = btn;
  }
  function closeTradeMenu() { tm.classList.remove('on'); tmOpenFor = null; }

  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.trade-btn');
    if (btn) { e.stopPropagation(); (tmOpenFor === btn) ? closeTradeMenu() : openTradeMenu(btn); return; }
    if (!e.target.closest('.trade-menu')) closeTradeMenu();
  });
  addEventListener('keydown', (e) => { if (e.key === 'Escape') closeTradeMenu(); });
  addEventListener('scroll', closeTradeMenu, { passive: true });
  addEventListener('resize', closeTradeMenu);
})();
