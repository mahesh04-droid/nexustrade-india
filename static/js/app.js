/**
 * NexusTrade India — Professional Trading Platform
 * Frontend Application Engine v3.0
 */

'use strict';

// ═══════════════════════════════════════════════════════════════
//  APP STATE
// ═══════════════════════════════════════════════════════════════
const state = {
  currentTab: 'terminal-tab',
  selectedSymbol: 'NIFTY50',
  selectedTimeframe: '1m',
  chartType: 'candle',
  indicators: { sma: true, ema: true, vwap: true, bb: false },
  assets: [],
  accounts: [],
  candles: [],
  indData: {},
  dom: { bids: [], asks: [] },
  presets: {},
  activeAlgos: {},
  orderHistory: [],
  riskStatus: { rules: {}, alerts: [] },
  backtestResult: null,
  marketMode: 'LIVE',
  liveConnected: false,
};

// Canvas references
let C = {};
let ctx = {};

function initCanvases() {
  C = {
    candle: document.getElementById('candlestickCanvas'),
    volume: document.getElementById('volumeCanvas'),
    rsi:    document.getElementById('rsiCanvas'),
    equity: document.getElementById('equityCanvas'),
  };

  ctx = {
    candle: C.candle?.getContext('2d'),
    volume: C.volume?.getContext('2d'),
    rsi:    C.rsi?.getContext('2d'),
    equity: C.equity?.getContext('2d'),
  };
}

// ═══════════════════════════════════════════════════════════════
//  INITIALIZATION
// ═══════════════════════════════════════════════════════════════
function init() {
  initCanvases();
  setupNav();
  setupListeners();
  setupChartResize();

  // Initial fetches
  fetchMarketMode();
  fetchAssets();
  fetchAccounts();
  fetchAlgoPresets();
  fetchRiskStatus();
  fetchOrderHistory();

  // Live data refresh loop (high frequency 500ms real-time stream)
  setInterval(refreshLive, 500);
}

// ═══════════════════════════════════════════════════════════════
//  NAVIGATION
// ═══════════════════════════════════════════════════════════════
function setupNav() {
  document.querySelectorAll('.nav-item[data-tab]').forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.dataset.tab;

      document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.workspace').forEach(w => w.classList.remove('active'));

      btn.classList.add('active');
      const tabEl = document.getElementById(tabId);
      if (tabEl) tabEl.classList.add('active');
      state.currentTab = tabId;

      if (tabId === 'terminal-tab') setTimeout(resizeCanvases, 30);
      else if (tabId === 'options-tab') fetchOptionChain();
      else if (tabId === 'backtest-tab' && state.backtestResult) setTimeout(renderEquityCurve, 30);
    });
  });
}

// ═══════════════════════════════════════════════════════════════
//  EVENT LISTENERS
// ═══════════════════════════════════════════════════════════════
function setupListeners() {
  // Option chain filters
  document.getElementById('optSymbolSelect')?.addEventListener('change', fetchOptionChain);
  document.getElementById('optExpirySelect')?.addEventListener('change', fetchOptionChain);

  // Instrument dropdown
  document.getElementById('instrumentSelectorBtn')?.addEventListener('click', () => {
    document.getElementById('instrumentDropdown')?.classList.toggle('open');
  });
  document.getElementById('instSearch')?.addEventListener('input', e => filterInstList(e.target.value));
  document.addEventListener('click', e => {
    if (!e.target.closest('#instrumentSelectorBtn') && !e.target.closest('#instrumentDropdown')) {
      document.getElementById('instrumentDropdown')?.classList.remove('open');
    }
  });

  // Timeframe buttons
  document.querySelectorAll('.chart-toolbar .tf-pill').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.chart-toolbar .tf-pill').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.selectedTimeframe = btn.dataset.tf;
      fetchCandles();
    });
  });

  // Watchlist filter tabs
  document.querySelectorAll('#wlTabs .tf-pill').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#wlTabs .tf-pill').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderWatchlist(btn.dataset.wl);
    });
  });

  // Chart type buttons
  document.querySelectorAll('.chart-type-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.chart-type-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.chartType = btn.dataset.type;
      renderCandleChart();
    });
  });

  // Indicator pills
  document.querySelectorAll('.ind-pill').forEach(btn => {
    btn.addEventListener('click', () => {
      btn.classList.toggle('active');
      const ind = btn.dataset.ind;
      state.indicators[ind] = btn.classList.contains('active');
      renderCandleChart();
    });
  });

  // Order Buttons
  document.getElementById('btnBuyMarket')?.addEventListener('click', () => placeOrder('BUY'));
  document.getElementById('btnSellMarket')?.addEventListener('click', () => placeOrder('SELL'));

  // Estimate value live update
  document.getElementById('ticketQuantity')?.addEventListener('input', updateEstimate);

  // Kill Switch
  document.getElementById('hdrKillSwitchBtn')?.addEventListener('click', triggerKillSwitch);
  document.getElementById('tabTriggerKillBtn')?.addEventListener('click', triggerKillSwitch);
  document.getElementById('tabResetKillBtn')?.addEventListener('click', resetKillSwitch);

  // Demo Showcase button
  document.getElementById('btnLaunchDemoShowcase')?.addEventListener('click', async () => {
    toast('info', 'Launching Demo Showcase', 'Executing sample trade & activating VWAP strategy...');
    const data = await api('/api/demo/setup', {method: 'POST'});
    if (data?.status === 'SUCCESS') {
      toast('success', 'Demo Showcase Active', data.message);
      fetchAccounts();
      fetchCandles();
      fetchAlgoPresets();
      fetchOrderHistory();
    }
  });

  // Mobile Dropdown Menu Toggle & Handlers
  const mmBtn   = document.getElementById('mobileMenuBtn');
  const mmDrawer= document.getElementById('mobileMenuDrawer');
  const mmClose = document.getElementById('mobileMenuClose');

  mmBtn?.addEventListener('click', () => mmDrawer?.classList.toggle('open'));
  mmClose?.addEventListener('click', () => mmDrawer?.classList.remove('open'));

  document.querySelectorAll('.mm-nav-item[data-tab]').forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.dataset.tab;
      document.querySelectorAll('.nav-item[data-tab]').forEach(b => {
        if (b.dataset.tab === tabId) b.click();
      });
      mmDrawer?.classList.remove('open');
    });
  });

  document.getElementById('mmBtnDemo')?.addEventListener('click', () => {
    document.getElementById('btnLaunchDemoShowcase')?.click();
    mmDrawer?.classList.remove('open');
  });

  document.getElementById('mmBtnAddAccount')?.addEventListener('click', () => {
    openModal('accountModal');
    mmDrawer?.classList.remove('open');
  });

  // Feed Toggle
  document.getElementById('feedToggleBtn')?.addEventListener('click', toggleMarketMode);

  // Account Modal
  document.getElementById('btnAddAccountBtn')?.addEventListener('click', () => openModal('accountModal'));
  document.getElementById('btnCloseAccModal')?.addEventListener('click', () => closeModal('accountModal'));
  document.getElementById('btnCancelAddAcc')?.addEventListener('click', () => closeModal('accountModal'));
  document.getElementById('btnSubmitAddAccount')?.addEventListener('click', submitAddAccount);
  document.getElementById('accountModal')?.addEventListener('click', e => {
    if (e.target === document.getElementById('accountModal')) closeModal('accountModal');
  });

  // Backtest
  document.getElementById('btnRunBacktest')?.addEventListener('click', runBacktest);

  // Risk Rules
  document.getElementById('btnSaveRiskRules')?.addEventListener('click', saveRiskRules);

  // Logout button
  document.getElementById('hdrLogoutBtn')?.addEventListener('click', async () => {
    await api('/api/auth/logout', {method: 'POST'});
    window.location.href = '/login';
  });

  // Chart canvas mouse move (crosshair)
  C.candle?.addEventListener('mousemove', onChartMouseMove);
  C.candle?.addEventListener('mouseleave', () => {
    const info = document.getElementById('crosshairInfo');
    if (info) info.style.display = 'none';
  });
}

// ═══════════════════════════════════════════════════════════════
//  CANVAS RESIZING
// ═══════════════════════════════════════════════════════════════
function setupChartResize() {
  const ro = new ResizeObserver(() => resizeCanvases());
  const wrap = document.getElementById('chartWrap');
  if (wrap) ro.observe(wrap);
  const ewrap = document.querySelector('.equity-curve-wrap');
  if (ewrap) ro.observe(ewrap);
}

function resizeCanvases() {
  const wrap = document.getElementById('chartWrap');
  if (wrap && C.candle) {
    const h = wrap.clientHeight - 130;
    C.candle.width  = wrap.clientWidth;
    C.candle.height = Math.max(h, 200);
    if (C.volume) { C.volume.width = wrap.clientWidth; C.volume.height = 50; }
    if (C.rsi)    { C.rsi.width   = wrap.clientWidth; C.rsi.height   = 80; }
    renderCandleChart();
  }
  const ewrap = document.querySelector('.equity-curve-wrap');
  if (ewrap && C.equity) {
    C.equity.width  = ewrap.clientWidth;
    C.equity.height = ewrap.clientHeight;
    renderEquityCurve();
  }
}

// ═══════════════════════════════════════════════════════════════
//  API HELPERS
// ═══════════════════════════════════════════════════════════════
async function api(path, opts = {}) {
  try {
    const res = await fetch(path, opts);
    if (res.status === 401 && !path.includes('/api/auth/')) {
      window.location.href = '/login';
      return null;
    }
    return await res.json();
  } catch(e) { console.error('API error', path, e); return null; }
}

async function fetchMarketMode() {
  const data = await api('/api/market/mode');
  if (!data) return;
  state.marketMode = data.mode;
  updateFeedUI();
}

async function toggleMarketMode() {
  const next = state.marketMode === 'LIVE' ? 'SIMULATED' : 'LIVE';
  const data = await api('/api/market/mode', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({mode: next})
  });
  if (!data) return;
  state.marketMode = data.mode;
  updateFeedUI();
  toast(data.mode === 'LIVE' ? 'success' : 'info',
        'Market Feed',
        data.mode === 'LIVE' ? 'Switched to Direct Official NSE Live Feed' : 'Switched to Simulated market mode');
  fetchAssets();
  fetchCandles();
}

function updateFeedUI() {
  const btn = document.getElementById('feedToggleBtn');
  const lbl = document.getElementById('feedModeLabel');
  const dot = btn?.querySelector('.feed-dot');
  const sb  = document.getElementById('globalStatusLabel');
  const sbs = document.getElementById('globalStatusSub');
  const sdot = document.getElementById('globalStatusDot');

  if (state.marketMode === 'LIVE') {
    btn?.classList.remove('simulated');
    if (dot) dot.className = 'feed-dot live';
    if (lbl) lbl.textContent = 'NSE LIVE';
    if (sb) sb.textContent = 'NSE Live Feed';
    if (sbs) sbs.textContent = 'Official NSE India Direct';
    sdot?.classList.remove('offline');
    state.liveConnected = true;
  } else {
    btn?.classList.add('simulated');
    if (dot) dot.className = 'feed-dot sim';
    if (lbl) lbl.textContent = 'SIMULATED';
    if (sb) sb.textContent = 'Simulated';
    if (sbs) sbs.textContent = 'Synthetic Engine';
    state.liveConnected = false;
  }
}

async function fetchAssets() {
  const data = await api('/api/assets');
  if (!data) return;
  state.assets = data;
  renderWatchlist();
  renderInstrumentDropdown();
  updateTopbar();
  updateEstimate();
}

async function fetchCandles() {
  const data = await api(`/api/candles/${state.selectedSymbol}?timeframe=${state.selectedTimeframe}`);
  if (!data) return;
  state.candles  = data.candles  || [];
  state.indData  = data.indicators || {};
  state.dom      = data.dom      || {bids:[], asks:[]};
  renderCandleChart();
  renderDOM();
  updateTopbar();
}

async function fetchAccounts() {
  const data = await api('/api/accounts');
  if (!data) return;
  
  const hash = JSON.stringify(data.map(a => [a.id, a.name, a.mode, a.type, a.balance, a.unrealized_pnl, a.open_positions_count]));
  const structureChanged = !state.lastAccountsHash || JSON.stringify(data.map(a => a.id)) !== JSON.stringify(state.accounts.map(a => a.id));
  
  state.accounts = data;
  
  if (hash !== state.lastAccountsHash) {
    state.lastAccountsHash = hash;
    renderAccountsGrid();
    if (structureChanged) renderAccountSelect();
  }
  updatePortfolioStrip();
}

async function fetchOptionChain() {
  const sym = document.getElementById('optSymbolSelect')?.value || 'NIFTY50';
  const exp = document.getElementById('optExpirySelect')?.value || '';
  const data = await api(`/api/options/chain/${sym}?expiry=${exp}`);
  if (!data) return;

  state.optionChain = data;
  renderOptionChain();
}

function renderOptionChain() {
  const tbody = document.getElementById('optionsChainBody');
  const pcrVal = document.getElementById('optPcrVal');
  const pcrStatus = document.getElementById('optPcrStatus');
  if (!tbody || !state.optionChain) return;

  const data = state.optionChain;
  if (pcrVal) pcrVal.textContent = data.pcr;
  if (pcrStatus) {
    pcrStatus.textContent = data.pcr >= 1.2 ? '(Strong Bullish)' : (data.pcr <= 0.8 ? '(Bearish)' : '(Neutral)');
    pcrStatus.style.color = data.pcr >= 1.0 ? '#10d982' : '#f43f5e';
  }

  tbody.innerHTML = data.chain.map(row => {
    const isAtm = row.is_atm;
    const strike = row.strike;
    const ce = row.call;
    const pe = row.put;

    const ceBg = ce.itm ? 'background:rgba(16,217,130,0.06);' : '';
    const peBg = pe.itm ? 'background:rgba(244,63,94,0.06);' : '';
    const atmBg = isAtm ? 'background:rgba(79,110,247,0.18); font-weight:700;' : '';

    return `
      <tr style="border-bottom:1px solid #141b28;">
        <!-- CALLS (CE) -->
        <td style="${ceBg} border-right:1px solid #1e2840; padding:0.4rem;">
          <div style="display:flex; gap:0.25rem; justify-content:center;">
            <button class="btn-small" style="background:#10d982; color:#000; font-weight:700; padding:0.25rem 0.45rem;" onclick="tradeOption('${data.symbol}', ${strike}, 'CE', 'BUY', ${ce.ltp}, ${data.lot_size})">BUY</button>
            <button class="btn-small" style="background:rgba(244,63,94,0.15); color:#f43f5e; padding:0.25rem 0.45rem;" onclick="tradeOption('${data.symbol}', ${strike}, 'CE', 'SELL', ${ce.ltp}, ${data.lot_size})">SELL</button>
          </div>
        </td>
        <td style="${ceBg} font-weight:600; color:#10d982;">₹${ce.ltp.toFixed(2)}</td>
        <td style="${ceBg} color:${ce.oi_chg>=0?'#10d982':'#f43f5e'};">${ce.oi_chg>=0?'+':''}${(ce.oi_chg/1000).toFixed(1)}k</td>
        <td style="${ceBg} color:#8a99ad;">${ce.iv}%</td>
        <td style="${ceBg} border-right:1px solid #1e2840; color:#a5b4d4;">${(ce.oi/1000).toFixed(1)}k</td>

        <!-- STRIKE PRICE -->
        <td style="${atmBg} color:#fff; font-weight:800; font-size:0.9rem; padding:0.5rem 0.8rem;">
          ${strike} ${isAtm ? '<span style="font-size:0.65rem; color:#4f6ef7; display:block;">ATM</span>' : ''}
        </td>

        <!-- PUTS (PE) -->
        <td style="${peBg} border-left:1px solid #1e2840; color:#a5b4d4;">${(pe.oi/1000).toFixed(1)}k</td>
        <td style="${peBg} color:#8a99ad;">${pe.iv}%</td>
        <td style="${peBg} color:${pe.oi_chg>=0?'#10d982':'#f43f5e'};">${pe.oi_chg>=0?'+':''}${(pe.oi_chg/1000).toFixed(1)}k</td>
        <td style="${peBg} font-weight:600; color:#f43f5e;">₹${pe.ltp.toFixed(2)}</td>
        <td style="${peBg} padding:0.4rem;">
          <div style="display:flex; gap:0.25rem; justify-content:center;">
            <button class="btn-small" style="background:#f43f5e; color:#fff; font-weight:700; padding:0.25rem 0.45rem;" onclick="tradeOption('${data.symbol}', ${strike}, 'PE', 'BUY', ${pe.ltp}, ${data.lot_size})">BUY</button>
            <button class="btn-small" style="background:rgba(16,217,130,0.15); color:#10d982; padding:0.25rem 0.45rem;" onclick="tradeOption('${data.symbol}', ${strike}, 'PE', 'SELL', ${pe.ltp}, ${data.lot_size})">SELL</button>
          </div>
        </td>
      </tr>`;
  }).join('');
}

window.tradeOption = async (indexSymbol, strike, optType, side, price, lotSize) => {
  const accId = document.getElementById('ticketAccountSelect')?.value;
  if (!accId) {
    toast('error', 'No Account Connected', 'Please connect a broker account under Accounts tab first.');
    return;
  }

  const optionSymbol = `${indexSymbol} ${strike} ${optType}`;
  toast('info', 'Executing Option Order', `${side} ${lotSize}x ${optionSymbol} @ ₹${price}...`);

  const data = await api('/api/orders/place', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({
      account_id: accId,
      symbol: optionSymbol,
      side: side,
      quantity: lotSize,
      type: 'MARKET',
      strategy: 'Option Chain Terminal'
    })
  });

  if (data?.status === 'SUCCESS') {
    toast('success', 'Option Order Executed', `${side} ${lotSize}x ${optionSymbol} filled @ ₹${price}`);
    fetchAccounts();
    fetchOrderHistory();
  } else {
    toast('error', 'Option Order Rejected', data?.message || 'Execution error');
  }
};

async function fetchAlgoPresets() {
  const data = await api('/api/algo/presets');
  if (!data) return;
  state.presets    = data.presets     || {};
  state.activeAlgos = data.active_algos || {};
  renderAlgoPresets();
}

async function fetchRiskStatus() {
  const data = await api('/api/risk/status');
  if (!data) return;
  state.riskStatus = data;
  renderRiskStatus();
}

async function fetchOrderHistory() {
  const data = await api('/api/orders/history');
  if (!data) return;
  state.orderHistory = data;
  renderOrderLogs();
}

function refreshLive() {
  fetchAssets();
  fetchCandles();
  fetchAccounts();
  fetchRiskStatus();
  fetchOrderHistory();
}

// ═══════════════════════════════════════════════════════════════
//  TOPBAR UPDATES
// ═══════════════════════════════════════════════════════════════
function updateTopbar() {
  const asset = state.assets.find(a => a.symbol === state.selectedSymbol);
  if (!asset) return;

  const symEl  = document.getElementById('topbarSymbol');
  const nameEl = document.getElementById('topbarSymbolName');
  if (symEl)  symEl.textContent  = asset.symbol;
  if (nameEl) nameEl.textContent = asset.name;

  const p = asset.price || 0;
  const chg = asset.change_pct || 0;
  const priceEl = document.getElementById('topbarPrice');
  const deltaEl = document.getElementById('topbarDelta');
  const deltaPctEl = document.getElementById('topbarDeltaPct');

  const absDelta = Math.abs((p * chg / 100)).toFixed(asset.decimals || 2);
  const sign = chg >= 0 ? '+' : '-';

  if (priceEl) {
    priceEl.textContent = `₹${p.toLocaleString(undefined, {minimumFractionDigits: asset.decimals||2})}`;
    priceEl.style.color = chg >= 0 ? 'var(--green)' : 'var(--red)';
  }
  if (deltaEl) {
    deltaEl.textContent = `${sign}₹${absDelta}`;
    deltaEl.style.color = chg >= 0 ? 'var(--green)' : 'var(--red)';
  }
  if (deltaPctEl) {
    deltaPctEl.textContent = `${sign}${Math.abs(chg).toFixed(2)}%`;
    deltaPctEl.style.color = chg >= 0 ? 'var(--green)' : 'var(--red)';
  }

  if (state.candles.length > 0) {
    const today = state.candles.slice(-60);
    const first = today[0];
    const openEl = document.getElementById('topbarOpen');
    const highEl = document.getElementById('topbarHigh');
    const lowEl  = document.getElementById('topbarLow');
    const volEl  = document.getElementById('topbarVol');

    if (openEl) openEl.textContent = `₹${first.open.toFixed(asset.decimals||2)}`;
    if (highEl) highEl.textContent = `₹${Math.max(...today.map(c=>c.high)).toFixed(asset.decimals||2)}`;
    if (lowEl)  lowEl.textContent  = `₹${Math.min(...today.map(c=>c.low)).toFixed(asset.decimals||2)}`;
    
    const vol = today.reduce((s,c) => s + (c.volume || 0), 0);
    if (volEl) volEl.textContent = vol > 1e6 ? `${(vol/1e6).toFixed(1)}M` : `${(vol/1e3).toFixed(0)}K`;
  }
}

function updatePortfolioStrip() {
  const master = state.accounts.find(a => a.type === 'Master') || state.accounts[0];
  if (!master) return;
  const eq = master.total_equity ?? master.balance ?? 0;
  const pnl = master.unrealized_pnl ?? 0;
  const eqEl = document.getElementById('hdrMasterEquity');
  const pnlEl = document.getElementById('hdrUnrealizedPnl');

  if (eqEl)  eqEl.textContent  = `₹${eq.toLocaleString(undefined,{minimumFractionDigits:2})}`;
  if (pnlEl) {
    pnlEl.textContent = `${pnl >= 0 ? '+' : ''}₹${pnl.toFixed(2)}`;
    pnlEl.className   = `port-val ${pnl >= 0 ? 'green' : 'red'}`;
  }
}

// ═══════════════════════════════════════════════════════════════
//  WATCHLIST
// ═══════════════════════════════════════════════════════════════
function renderWatchlist(filter = 'all') {
  const container = document.getElementById('watchlistContainer');
  if (!container) return;

  const filtered = filter === 'all' ? state.assets : state.assets.filter(a => {
    if (filter === 'indices') return a.category === 'Indices';
    if (filter === 'equities') return a.category === 'Equities';
    return true;
  });

  container.innerHTML = filtered.map(asset => {
    const chg = asset.change_pct ?? 0;
    const sign = chg >= 0 ? '+' : '';
    return `
      <div class="wl-item ${asset.symbol === state.selectedSymbol ? 'active' : ''}" onclick="selectSymbol('${asset.symbol}')">
        <div class="wl-left">
          <span class="wl-symbol">${asset.symbol}</span>
          <span class="wl-name">${asset.category || ''}</span>
        </div>
        <div class="wl-right">
          <span class="wl-price">₹${asset.price?.toLocaleString(undefined,{minimumFractionDigits:asset.decimals||2})}</span>
          <span class="wl-change ${chg >= 0 ? 'up' : 'dn'}">${sign}${Math.abs(chg).toFixed(2)}%</span>
        </div>
      </div>`;
  }).join('');
}

window.selectSymbol = (symbol) => {
  state.selectedSymbol = symbol;
  const ticketInput = document.getElementById('ticketSymbol');
  if (ticketInput) ticketInput.value = symbol;
  renderWatchlist();
  fetchCandles();
  updateTopbar();
  updateEstimate();
  document.getElementById('instrumentDropdown')?.classList.remove('open');
};

// ═══════════════════════════════════════════════════════════════
//  INSTRUMENT DROPDOWN
// ═══════════════════════════════════════════════════════════════
function renderInstrumentDropdown(filter = '') {
  const list = document.getElementById('instList');
  if (!list) return;

  const filtered = filter
    ? state.assets.filter(a => a.symbol.includes(filter.toUpperCase()) || a.name.toLowerCase().includes(filter.toLowerCase()))
    : state.assets;

  list.innerHTML = filtered.map(a => {
    const chg = a.change_pct ?? 0;
    return `
      <div class="inst-row" onclick="selectSymbol('${a.symbol}')">
        <div class="inst-row-left">
          <span class="inst-row-sym">${a.symbol}</span>
          <span class="inst-row-name">${a.name}</span>
        </div>
        <span class="inst-row-cat">${a.category}</span>
        <span class="inst-row-price ${chg>=0?'green':'red'}">₹${a.price?.toFixed(a.decimals||2)}</span>
      </div>`;
  }).join('');
}

function filterInstList(q) {
  renderInstrumentDropdown(q);
}

// ═══════════════════════════════════════════════════════════════
//  CANDLESTICK CHART RENDERER
// ═══════════════════════════════════════════════════════════════
function renderCandleChart() {
  if (!ctx.candle || !C.candle || state.candles.length === 0) return;

  const W = C.candle.width;
  const H = C.candle.height;
  const PAD = { top: 20, right: 65, bottom: 4, left: 8 };

  const cx  = ctx.candle;
  const candles = state.candles.slice(-100);
  const N = candles.length;
  if (N === 0) return;

  let lo = Math.min(...candles.map(c => c.low));
  let hi = Math.max(...candles.map(c => c.high));
  const range = hi - lo || 1;
  lo -= range * 0.04;
  hi += range * 0.04;

  const chartW = W - PAD.left - PAD.right;
  const chartH = H - PAD.top - PAD.bottom;
  const cw = (chartW / N) * 0.65;
  const gap = (chartW / N) * 0.35;

  const toY = p => PAD.top + chartH - ((p - lo) / (hi - lo)) * chartH;
  const toX = i => PAD.left + i * (cw + gap) + cw / 2;

  cx.clearRect(0, 0, W, H);
  cx.fillStyle = '#070a10';
  cx.fillRect(0, 0, W, H);

  // Gridlines
  const gridLines = 6;
  for (let i = 0; i <= gridLines; i++) {
    const y = PAD.top + (chartH / gridLines) * i;
    const pv = hi - ((hi - lo) / gridLines) * i;
    cx.strokeStyle = '#1e2840';
    cx.lineWidth = 1;
    cx.beginPath(); cx.moveTo(PAD.left, y); cx.lineTo(W - PAD.right, y); cx.stroke();
    cx.fillStyle = '#4c5a72';
    cx.font = '10px JetBrains Mono, monospace';
    cx.textAlign = 'left';
    cx.fillText(`₹${pv.toFixed(2)}`, W - PAD.right + 6, y + 4);
  }

  // Indicators — SMA
  if (state.indicators.sma && state.indData.sma_20) {
    drawLine(cx, state.indData.sma_20.slice(-N), N, toX, toY, '#f59e0b', 1.5, 0.7);
    drawLine(cx, state.indData.sma_50.slice(-N), N, toX, toY, '#06b6d4', 1.5, 0.7);
  }

  // Indicators — EMA
  if (state.indicators.ema && state.indData.ema_9) {
    drawLine(cx, state.indData.ema_9.slice(-N), N, toX, toY, '#8b5cf6', 1.5, 0.7);
  }

  // Indicators — VWAP
  if (state.indicators.vwap && state.indData.vwap) {
    drawLine(cx, state.indData.vwap.slice(-N), N, toX, toY, '#10d982', 1.8, 0.9);
  }

  // Indicators — Bollinger Bands
  if (state.indicators.bb && state.indData.bb_upper) {
    drawLine(cx, state.indData.bb_upper.slice(-N), N, toX, toY, '#4f6ef7', 1, 0.5);
    drawLine(cx, state.indData.bb_lower.slice(-N), N, toX, toY, '#4f6ef7', 1, 0.5);
    drawFill(cx, state.indData.bb_upper.slice(-N), state.indData.bb_lower.slice(-N), N, toX, toY, 'rgba(79,110,247,0.05)');
  }

  // Candles or Line
  if (state.chartType === 'line') {
    drawLine(cx, candles.map(c => c.close), N, toX, toY, '#4f6ef7', 2, 1);
  } else {
    candles.forEach((c, i) => {
      const x   = toX(i);
      const oY  = toY(c.open);
      const cY  = toY(c.close);
      const hY  = toY(c.high);
      const lY  = toY(c.low);
      const green = c.close >= c.open;
      const col = green ? '#10d982' : '#f43f5e';
      const bodyH = Math.max(Math.abs(cY - oY), 1.5);
      const bodyY = Math.min(oY, cY);

      cx.strokeStyle = green ? 'rgba(16,217,130,0.6)' : 'rgba(244,63,94,0.6)';
      cx.lineWidth = 1;
      cx.beginPath(); cx.moveTo(x, hY); cx.lineTo(x, lY); cx.stroke();

      if (green) {
        cx.strokeStyle = col;
        cx.lineWidth = 1;
        cx.fillStyle = bodyH > 3 ? 'rgba(16,217,130,0.15)' : col;
        cx.fillRect(x - cw/2, bodyY, cw, bodyH);
        cx.strokeRect(x - cw/2, bodyY, cw, bodyH);
      } else {
        cx.fillStyle = col;
        cx.fillRect(x - cw/2, bodyY, cw, bodyH);
      }
    });
  }

  renderVolumeChart(candles, N, toX, cw);
  renderRSIChart(state.indData.rsi_14?.slice(-N) || [], N, toX);
}

function drawLine(cx, vals, N, toX, toY, color, width=1.5, alpha=1) {
  if (!vals || vals.length === 0) return;
  cx.save();
  cx.globalAlpha = alpha;
  cx.strokeStyle = color;
  cx.lineWidth = width;
  cx.beginPath();
  let started = false;
  vals.forEach((v, i) => {
    if (!v || v <= 0) return;
    const x = toX(i), y = toY(v);
    if (!started) { cx.moveTo(x, y); started = true; }
    else cx.lineTo(x, y);
  });
  cx.stroke();
  cx.restore();
}

function drawFill(cx, upperVals, lowerVals, N, toX, toY, fillColor) {
  cx.save();
  cx.fillStyle = fillColor;
  cx.beginPath();
  for (let i = 0; i < N; i++) {
    const y = toY(upperVals[i] || 0);
    if (i === 0) cx.moveTo(toX(i), y); else cx.lineTo(toX(i), y);
  }
  for (let i = N - 1; i >= 0; i--) {
    cx.lineTo(toX(i), toY(lowerVals[i] || 0));
  }
  cx.closePath(); cx.fill();
  cx.restore();
}

function renderVolumeChart(candles, N, toX, cw) {
  if (!ctx.volume || !C.volume) return;
  const W = C.volume.width, H = C.volume.height;
  const vcx = ctx.volume;
  vcx.clearRect(0, 0, W, H);
  const maxVol = Math.max(...candles.map(c => c.volume), 1);

  candles.forEach((c, i) => {
    const barH = (c.volume / maxVol) * H;
    const x = toX(i);
    vcx.fillStyle = c.close >= c.open ? 'rgba(16,217,130,0.3)' : 'rgba(244,63,94,0.3)';
    vcx.fillRect(x - cw/2, H - barH, cw, barH);
  });
}

function renderRSIChart(rsiVals, N, toX) {
  if (!ctx.rsi || !C.rsi || !rsiVals.length) return;
  const W = C.rsi.width, H = C.rsi.height;
  const rcx = ctx.rsi;
  const PAD_R = 65, PAD_L = 8;
  rcx.clearRect(0, 0, W, H);

  rcx.fillStyle = '#0c1018';
  rcx.fillRect(0, 0, W, H);

  const toRX = i => PAD_L + i * ((W - PAD_L - PAD_R) / N);
  const toRY = v => H - (v / 100) * H;

  [[70, 'rgba(244,63,94,0.2)'], [30, 'rgba(16,217,130,0.2)'], [50, 'rgba(255,255,255,0.05)']].forEach(([v, c]) => {
    rcx.strokeStyle = c;
    rcx.lineWidth = 1;
    rcx.setLineDash([3, 3]);
    rcx.beginPath(); rcx.moveTo(PAD_L, toRY(v)); rcx.lineTo(W - PAD_R, toRY(v)); rcx.stroke();
    rcx.setLineDash([]);
  });

  rcx.strokeStyle = '#8b5cf6';
  rcx.lineWidth = 1.5;
  rcx.beginPath();
  rsiVals.forEach((v, i) => {
    if (!v) return;
    const x = toRX(i), y = toRY(v);
    if (i === 0) rcx.moveTo(x, y); else rcx.lineTo(x, y);
  });
  rcx.stroke();

  rcx.fillStyle = '#4c5a72';
  rcx.font = '9px JetBrains Mono';
  rcx.textAlign = 'left';
  rcx.fillText('70', W - PAD_R + 4, toRY(70) + 3);
  rcx.fillText('30', W - PAD_R + 4, toRY(30) + 3);
  const last = rsiVals.filter(Boolean).at(-1);
  if (last) {
    rcx.fillStyle = '#8b5cf6';
    rcx.fillText(last.toFixed(1), W - PAD_R + 4, toRY(last) + 3);
  }
}

// ═══════════════════════════════════════════════════════════════
//  CHART CROSSHAIR
// ═══════════════════════════════════════════════════════════════
function onChartMouseMove(e) {
  if (!C.candle || state.candles.length === 0) return;
  const rect = C.candle.getBoundingClientRect();
  const x = (e.clientX - rect.left) * (C.candle.width / rect.width);
  const N = Math.min(state.candles.length, 100);
  const cw = (C.candle.width / N) * 0.65;
  const gap = (C.candle.width / N) * 0.35;
  const idx = Math.floor(x / (cw + gap));
  const candles = state.candles.slice(-N);
  if (idx < 0 || idx >= candles.length) return;

  const c = candles[idx];
  const info = document.getElementById('crosshairInfo');
  const tEl = document.getElementById('ciTime');
  const oEl = document.getElementById('ciOpen');
  const hEl = document.getElementById('ciHigh');
  const lEl = document.getElementById('ciLow');
  const cEl = document.getElementById('ciClose');
  const vEl = document.getElementById('ciVol');

  if (tEl) tEl.textContent = c.time_str || '';
  if (oEl) oEl.textContent = `₹${c.open}`;
  if (hEl) hEl.textContent = `₹${c.high}`;
  if (lEl) lEl.textContent = `₹${c.low}`;
  if (cEl) cEl.textContent = `₹${c.close}`;
  if (vEl) vEl.textContent = c.volume?.toLocaleString() || '';
  if (info) info.style.display = 'flex';
}

// ═══════════════════════════════════════════════════════════════
//  DOM (Depth of Market)
// ═══════════════════════════════════════════════════════════════
function renderDOM() {
  const rows = document.getElementById('domRows');
  const spreadEl = document.getElementById('domSpread');
  const labelEl  = document.getElementById('domSymbolLabel');
  if (!rows) return;

  if (labelEl) labelEl.textContent = state.selectedSymbol;
  const bids = state.dom.bids || [];
  const asks = state.dom.asks || [];

  if (bids.length && asks.length) {
    const spread = Math.abs(asks[0].price - bids[0].price);
    if (spreadEl) spreadEl.textContent = `₹${spread.toFixed(2)}`;
  }

  rows.innerHTML = Array.from({length: 5}, (_, i) => {
    const bid = bids[i] || {price: '—', volume: '—'};
    const ask = asks[i] || {price: '—', volume: '—'};
    return `
      <div class="dom-row">
        <span class="dom-bid-vol">${bid.volume}</span>
        <span class="dom-bid-price">${typeof bid.price==='number' ? '₹'+bid.price.toFixed(2) : bid.price}</span>
        <span class="dom-ask-price">${typeof ask.price==='number' ? '₹'+ask.price.toFixed(2) : ask.price}</span>
        <span class="dom-ask-vol">${ask.volume}</span>
      </div>`;
  }).join('');
}

// ═══════════════════════════════════════════════════════════════
//  ORDER TICKET
// ═══════════════════════════════════════════════════════════════
function renderAccountSelect() {
  const sel = document.getElementById('ticketAccountSelect');
  if (!sel) return;

  if (!state.accounts || state.accounts.length === 0) {
    sel.innerHTML = `<option value="">No Accounts Linked — Connect Broker Account First</option>`;
    updateModebadge();
    return;
  }

  sel.innerHTML = state.accounts.map(a =>
    `<option value="${a.id}">${a.name} (${a.type} · ${a.mode})</option>`
  ).join('');
  updateModebadge();
  sel.addEventListener('change', updateModebadge);
}

function updateModebadge() {
  const sel = document.getElementById('ticketAccountSelect');
  const badge = document.getElementById('ticketModeBadge');
  if (!sel || !badge) return;
  const acc = state.accounts.find(a => a.id === sel.value);
  if (!acc) {
    badge.textContent = 'None';
    badge.className = 'mode-badge paper';
    return;
  }
  badge.textContent = acc.mode;
  badge.className = `mode-badge ${acc.mode === 'Live' ? 'live' : 'paper'}`;
}

function updateEstimate() {
  const qty = parseFloat(document.getElementById('ticketQuantity')?.value) || 0;
  const asset = state.assets.find(a => a.symbol === state.selectedSymbol);
  const price = asset?.price || 0;
  const est = qty * price;
  const el = document.getElementById('estValue');
  if (el) el.textContent = `₹${est.toLocaleString(undefined,{minimumFractionDigits:2})}`;
}

async function placeOrder(side) {
  const accId  = document.getElementById('ticketAccountSelect')?.value;
  if (!accId) {
    toast('error', 'No Account Connected', 'Please connect a broker account under Accounts tab first.');
    return;
  }
  const symbol = state.selectedSymbol;
  const qty    = parseInt(document.getElementById('ticketQuantity')?.value) || 1;
  const type   = document.getElementById('ticketOrderType')?.value || 'MARKET';

  const data = await api('/api/orders/place', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({account_id:accId, symbol, side, quantity:qty, type, strategy:'Manual Terminal'})
  });

  if (data?.status === 'SUCCESS') {
    const copyCnt = data.order?.copied_orders?.length || 0;
    toast('success', `Order Executed`, `${side} ${qty}× ${symbol} filled${copyCnt ? ` · ${copyCnt} child copies` : ''}`);
    fetchAccounts();
    fetchOrderHistory();
  } else {
    toast('error', 'Order Rejected', data?.message || 'Unknown error');
  }
}

// ═══════════════════════════════════════════════════════════════
//  ACCOUNTS GRID
// ═══════════════════════════════════════════════════════════════
function renderAccountsGrid() {
  const grid = document.getElementById('accountsGridContainer');
  if (!grid) return;

  if (!state.accounts || state.accounts.length === 0) {
    grid.innerHTML = `
      <div class="panel" style="grid-column:1/-1; padding:3rem 1.5rem; text-align:center;">
        <div style="width:52px; height:52px; background:rgba(79,110,247,0.12); border-radius:50%; display:flex; align-items:center; justify-content:center; margin:0 auto 1rem;">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#4f6ef7" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="17" y1="11" x2="23" y2="11"/></svg>
        </div>
        <h3 style="color:#fff; font-size:1.1rem; font-weight:700; margin-bottom:0.4rem;">No Linked Broker Accounts</h3>
        <p style="color:#8a99ad; font-size:0.82rem; margin-bottom:1.5rem;">Connect your primary Master account (Zerodha, AngelOne, Upstox, Dhan) to start trading.</p>
        <button class="btn-primary" onclick="openModal('accountModal')">
          + Connect Master Broker Account
        </button>
      </div>`;
    return;
  }

  grid.innerHTML = state.accounts.map(acc => {
    const pnl = acc.unrealized_pnl ?? 0;
    const eq  = acc.total_equity   ?? acc.balance;
    const pnlSign = pnl >= 0 ? '+' : '';

    return `
      <div class="account-card">
        <div class="acc-card-header">
          <div>
            <div class="acc-name">${acc.name}</div>
            <div class="acc-id">${acc.id}</div>
          </div>
          <div class="acc-badges">
            <span class="badge badge-${acc.type.toLowerCase()}">${acc.type}</span>
            <span class="badge badge-${acc.mode.toLowerCase()}">${acc.mode}</span>
          </div>
        </div>

        <div class="acc-stats">
          <div class="acc-stat">
            <div class="acc-stat-label">Balance</div>
            <div class="acc-stat-val">₹${(acc.balance||0).toLocaleString(undefined,{minimumFractionDigits:2})}</div>
          </div>
          <div class="acc-stat">
            <div class="acc-stat-label">Total Equity</div>
            <div class="acc-stat-val">₹${eq.toLocaleString(undefined,{minimumFractionDigits:2})}</div>
          </div>
          <div class="acc-stat">
            <div class="acc-stat-label">Unrealized P&amp;L</div>
            <div class="acc-stat-val ${pnl>=0?'green':'red'}">${pnlSign}₹${pnl.toFixed(2)}</div>
          </div>
          <div class="acc-stat">
            <div class="acc-stat-label">Open Positions</div>
            <div class="acc-stat-val">${acc.open_positions_count || 0}</div>
          </div>
        </div>

        <div class="acc-broker-info">
          <b>Broker:</b> ${acc.broker}
          ${acc.multiplier !== undefined ? `<br><b>Multiplier:</b> ${acc.multiplier}×` : ''}
          ${acc.copied_by?.length ? `<br><b>Copies to:</b> ${acc.copied_by.join(', ')}` : ''}
        </div>

        <div class="acc-actions" style="display:flex; gap:0.4rem; flex-wrap:wrap; margin-top:0.75rem;">
          <button class="btn-small" onclick="toggleAccountMode('${acc.id}','${acc.mode==='Live'?'Paper':'Live'}')">
            Switch to ${acc.mode==='Live'?'Paper':'Live Mode'}
          </button>
          ${acc.broker.includes('Angel') ? `<button class="btn-small" style="background:rgba(16,217,130,0.15); color:var(--green);" onclick="syncBrokerBalance('${acc.id}')">🔄 Sync Live Balance</button>` : ''}
          <button class="btn-small" style="background:rgba(244,63,94,0.15); color:var(--red);" onclick="deleteAccount('${acc.id}')">🗑 Remove</button>
        </div>
      </div>`;
  }).join('');
}

window.toggleAccountMode = async (accId, newMode) => {
  const data = await api(`/api/accounts/${accId}`, {
    method: 'PUT',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({mode: newMode})
  });
  if (data?.status === 'SUCCESS') {
    toast('info', 'Mode Switched', `Account switched to ${newMode} mode`);
    fetchAccounts();
  }
};

window.syncBrokerBalance = async (accId) => {
  toast('info', 'Syncing Balance', 'Fetching live funds & profile from broker servers...');
  const data = await api(`/api/accounts/${accId}/sync`, {method: 'POST'});
  if (data?.status === 'SUCCESS') {
    toast('success', 'Balance Synced', data.message);
    fetchAccounts();
  } else {
    toast('error', 'Sync Failed', data?.message || 'Check credentials');
  }
};

window.deleteAccount = async (accId) => {
  if (!confirm('Are you sure you want to remove this account profile?')) return;
  const data = await api(`/api/accounts/${accId}`, {method: 'DELETE'});
  if (data?.status === 'SUCCESS') {
    toast('info', 'Account Removed', data.message);
    fetchAccounts();
  }
};

window.clearAllAccounts = async () => {
  if (!confirm('⚠ REMOVE ALL ACCOUNTS?\n\nThis will clear all connected account profiles so you can add your own real account.')) return;
  const data = await api('/api/accounts/clear', {method: 'POST'});
  if (data?.status === 'SUCCESS') {
    toast('info', 'Accounts Cleared', 'All account profiles removed.');
    fetchAccounts();
  }
};

// ═══════════════════════════════════════════════════════════════
//  ALGO STUDIO
// ═══════════════════════════════════════════════════════════════
function renderAlgoPresets() {
  const container = document.getElementById('algoPresetsContainer');
  const monitorBody = document.getElementById('algoMonitorBody');
  if (!container) return;

  const activeCount = Object.values(state.activeAlgos).filter(a => a.status === 'RUNNING').length;
  const countEl = document.getElementById('activeAlgoCount');
  if (countEl) countEl.textContent = `${activeCount} Active`;

  container.innerHTML = Object.entries(state.presets).map(([key, strat]) => {
    const algoId = `${state.selectedSymbol}_${key}`;
    const active = state.activeAlgos[algoId];
    const running = active?.status === 'RUNNING';

    return `
      <div class="algo-card">
        <div class="algo-card-header">
          <div class="algo-card-name">${strat.name}</div>
          <span class="algo-status-badge ${running?'running':'stopped'}">${running?'RUNNING':'STOPPED'}</span>
        </div>
        <div class="algo-card-desc">${strat.desc}</div>
        <div class="algo-card-footer">
          <span class="algo-tf-tag">⏱ ${strat.params?.timeframe || '5m'} · ${state.selectedSymbol}</span>
          <button class="btn-algo-toggle ${running?'stop':'start'}" onclick="toggleAlgo('${key}')">
            ${running ? '⏹ Stop' : '▶ Activate'}
          </button>
        </div>
      </div>`;
  }).join('');

  const runningAlgos = Object.values(state.activeAlgos).filter(a => a.status === 'RUNNING');
  if (monitorBody) {
    if (runningAlgos.length === 0) {
      monitorBody.innerHTML = `
        <div class="empty-state">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          <p>No active strategies running</p>
          <span>Activate a strategy from the library</span>
        </div>`;
    } else {
      monitorBody.innerHTML = runningAlgos.map(a => `
        <div class="algo-card" style="margin-bottom:0.5rem">
          <div class="algo-card-header">
            <div class="algo-card-name">${a.strategy_name}</div>
            <span class="algo-status-badge running">RUNNING</span>
          </div>
          <div class="algo-card-desc">
            Symbol: <b>${a.symbol}</b> &nbsp;|&nbsp;
            Signals: <b>${a.signals_generated}</b> &nbsp;|&nbsp;
            Started: ${a.start_time}
          </div>
          <div class="algo-card-footer">
            <span class="algo-tf-tag">Last: ${a.last_signal || 'No signal yet'}</span>
            <button class="btn-algo-toggle stop" onclick="toggleAlgo('${a.strategy_key}')">⏹ Stop</button>
          </div>
        </div>`).join('');
    }
  }
}

window.toggleAlgo = async (stratKey) => {
  const master = state.accounts.find(a => a.type === 'Master') || state.accounts[0];
  const data = await api('/api/algo/toggle', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({symbol: state.selectedSymbol, strategy_key: stratKey, account_id: master?.id || 'ACC-MASTER-01'})
  });
  if (data?.status === 'SUCCESS') {
    toast('info', 'Strategy Update', data.message);
    fetchAlgoPresets();
  }
};

// ═══════════════════════════════════════════════════════════════
//  BACKTEST
// ═══════════════════════════════════════════════════════════════
async function runBacktest() {
  const btn = document.getElementById('btnRunBacktest');
  if (btn) { btn.textContent = 'Running…'; btn.disabled = true; }

  const data = await api('/api/algo/backtest', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({
      symbol:   document.getElementById('btSymbolSelect')?.value   || 'NIFTY50',
      strategy_key: document.getElementById('btStrategySelect')?.value || 'MA_CROSSOVER',
      timeframe: document.getElementById('btTimeframeSelect')?.value || '15m',
      initial_capital: parseFloat(document.getElementById('btCapital')?.value || '1000000'),
    })
  });

  if (btn) { btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Run Backtest'; btn.disabled = false; }
  if (!data || data.error) { toast('error', 'Backtest Failed', data?.error || 'Check console'); return; }

  state.backtestResult = data;
  const s = data.summary;

  const npEl = document.getElementById('btNetProfit');
  const retEl = document.getElementById('btReturn');
  const wrEl = document.getElementById('btWinRate');
  const pfEl = document.getElementById('btProfitFactor');
  const ddEl = document.getElementById('btMaxDrawdown');
  const ttEl = document.getElementById('btTotalTrades');

  if (npEl)  { npEl.textContent  = `₹${s.net_profit.toLocaleString(undefined,{minimumFractionDigits:2})}`; npEl.className = `btm-val ${s.net_profit >= 0 ? 'green' : 'red'}`; }
  if (retEl) { retEl.textContent = `${s.return_pct >= 0 ? '+' : ''}${s.return_pct}%`; retEl.className = `btm-val ${s.return_pct >= 0 ? 'green' : 'red'}`; }
  if (wrEl)  wrEl.textContent  = `${s.win_rate}%`;
  if (pfEl)  pfEl.textContent  = s.profit_factor;
  if (ddEl)  ddEl.textContent  = `-${s.max_drawdown_pct}%`;
  if (ttEl)  ttEl.textContent  = s.total_trades;

  renderEquityCurve();

  const tbody = document.getElementById('btTradesBody');
  if (tbody && data.trades) {
    tbody.innerHTML = data.trades.slice(0, 30).map(t => `
      <tr>
        <td>${t.entry_time}</td><td>${t.exit_time}</td>
        <td><span class="badge badge-${t.side==='BUY'?'live':'master'}">${t.side}</span></td>
        <td>₹${t.entry_price.toFixed(2)}</td><td>₹${t.exit_price.toFixed(2)}</td>
        <td class="${t.pnl>=0?'green':'red'}">₹${t.pnl.toFixed(2)}</td>
        <td class="${t.return_pct>=0?'green':'red'}">${t.return_pct}%</td>
      </tr>`).join('');
  }

  toast('success', 'Backtest Complete', `${s.total_trades} trades · Win Rate: ${s.win_rate}%`);
}

function renderEquityCurve() {
  if (!ctx.equity || !C.equity || !state.backtestResult) return;
  const pts = state.backtestResult.equity_curve || [];
  if (pts.length < 2) return;

  const W = C.equity.width, H = C.equity.height;
  const PAD = { t: 20, r: 10, b: 20, l: 10 };
  const ecx = ctx.equity;

  const vals = pts.map(p => p.equity);
  const minV = Math.min(...vals);
  const maxV = Math.max(...vals);
  const rangeV = maxV - minV || 1;

  const initial = vals[0];
  const toX = i => PAD.l + (i / (pts.length - 1)) * (W - PAD.l - PAD.r);
  const toY = v => PAD.t + (H - PAD.t - PAD.b) - ((v - minV) / rangeV) * (H - PAD.t - PAD.b);

  ecx.clearRect(0, 0, W, H);

  const grad = ecx.createLinearGradient(0, PAD.t, 0, H - PAD.b);
  grad.addColorStop(0, 'rgba(16,217,130,0.25)');
  grad.addColorStop(1, 'rgba(16,217,130,0)');

  ecx.beginPath();
  pts.forEach((p, i) => {
    const x = toX(i), y = toY(p.equity);
    if (i === 0) ecx.moveTo(x, y); else ecx.lineTo(x, y);
  });
  ecx.lineTo(toX(pts.length-1), H-PAD.b);
  ecx.lineTo(toX(0), H-PAD.b);
  ecx.closePath();
  ecx.fillStyle = grad;
  ecx.fill();

  ecx.strokeStyle = '#10d982';
  ecx.lineWidth = 2;
  ecx.beginPath();
  pts.forEach((p, i) => {
    const x = toX(i), y = toY(p.equity);
    if (i === 0) ecx.moveTo(x, y); else ecx.lineTo(x, y);
  });
  ecx.stroke();

  const baseY = toY(initial);
  ecx.strokeStyle = 'rgba(255,255,255,0.08)';
  ecx.lineWidth = 1;
  ecx.setLineDash([4, 4]);
  ecx.beginPath(); ecx.moveTo(PAD.l, baseY); ecx.lineTo(W - PAD.r, baseY); ecx.stroke();
  ecx.setLineDash([]);
}

// ═══════════════════════════════════════════════════════════════
//  RISK GUARD
// ═══════════════════════════════════════════════════════════════
function renderRiskStatus() {
  const alerts = state.riskStatus.alerts || [];
  const feed = document.getElementById('riskAlertsFeed');
  const countEl = document.getElementById('auditCount');
  const ksStatus = document.getElementById('ksStatus');
  const ksRules = state.riskStatus.rules || {};

  const dlEl = document.getElementById('riskMaxDailyLoss');
  const psEl = document.getElementById('riskMaxPosSize');
  const slEl = document.getElementById('riskStopLossPct');
  const tpEl = document.getElementById('riskTakeProfitPct');
  if (dlEl && ksRules.max_daily_loss) dlEl.value = ksRules.max_daily_loss;
  if (psEl && ksRules.max_position_size) psEl.value = ksRules.max_position_size;
  if (slEl && ksRules.default_stop_loss_pct) slEl.value = ksRules.default_stop_loss_pct;
  if (tpEl && ksRules.default_take_profit_pct) tpEl.value = ksRules.default_take_profit_pct;

  if (ksStatus) {
    if (ksRules.kill_switch_active) {
      ksStatus.className = 'ks-status danger';
      ksStatus.innerHTML = `<div class="ks-status-dot"></div><span>Kill Switch ACTIVE — All Trading Halted</span>`;
    } else {
      ksStatus.className = 'ks-status';
      ksStatus.innerHTML = `<div class="ks-status-dot" style="animation: pulse-green 2s infinite"></div><span>Kill Switch Inactive — Trading Allowed</span>`;
    }
  }

  if (countEl) countEl.textContent = `${alerts.length} alerts`;
  if (!feed) return;

  if (alerts.length === 0) {
    feed.innerHTML = `<div class="empty-state" style="padding:1rem 0"><p style="font-size:0.8rem">No risk events recorded</p></div>`;
    return;
  }

  feed.innerHTML = alerts.map(a => `
    <div class="audit-entry">
      <span class="audit-time">${a.timestamp}</span>
      <span class="audit-level-${a.level}">[${a.level}]</span>
      <span class="audit-msg">${a.text}</span>
    </div>`).join('');
}

async function triggerKillSwitch() {
  if (!confirm('⚠ EMERGENCY: Activate Global Kill Switch?\n\nThis will immediately liquidate ALL open positions across all accounts and halt all active algorithms.')) return;
  const data = await api('/api/risk/kill-switch', {method:'POST'});
  if (data) {
    toast('error', '🚨 Kill Switch Activated', data.message);
    fetchRiskStatus();
    fetchAccounts();
    fetchOrderHistory();
  }
}

async function resetKillSwitch() {
  const data = await api('/api/risk/kill-switch/reset', {method:'POST'});
  if (data) {
    toast('success', 'Kill Switch Reset', 'Trading has been re-enabled');
    fetchRiskStatus();
  }
}

async function saveRiskRules() {
  const data = await api('/api/risk/update', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({
      max_daily_loss:        parseFloat(document.getElementById('riskMaxDailyLoss')?.value || 25000),
      max_position_size:     parseFloat(document.getElementById('riskMaxPosSize')?.value || 500000),
      default_stop_loss_pct: parseFloat(document.getElementById('riskStopLossPct')?.value || 1.5),
      default_take_profit_pct: parseFloat(document.getElementById('riskTakeProfitPct')?.value || 3.0),
    })
  });
  if (data?.status === 'SUCCESS') {
    toast('success', 'Risk Rules Saved', 'Circuit breakers updated successfully');
    fetchRiskStatus();
  }
}

// ═══════════════════════════════════════════════════════════════
//  ORDER LOGS
// ═══════════════════════════════════════════════════════════════
function renderOrderLogs() {
  const tbody = document.getElementById('orderLogsTableBody');
  const filterSide = document.getElementById('logsFilterSide')?.value || 'all';
  if (!tbody) return;

  const logs = filterSide === 'all'
    ? state.orderHistory
    : state.orderHistory.filter(o => o.side === filterSide);

  if (logs.length === 0) {
    tbody.innerHTML = `<tr class="empty-row"><td colspan="10">No orders yet</td></tr>`;
    return;
  }

  tbody.innerHTML = logs.map(o => `
    <tr>
      <td>${o.timestamp}</td>
      <td>${o.order_id}</td>
      <td>${o.account_name}</td>
      <td><b>${o.symbol}</b></td>
      <td><span class="badge badge-${o.side==='BUY'?'live':'master'}">${o.side}</span></td>
      <td>${o.quantity}</td>
      <td>₹${(o.price||0).toFixed(2)}</td>
      <td>${o.strategy}</td>
      <td style="font-size:0.68rem;color:var(--text-3)">${(o.copied_orders||[]).join(', ')||'—'}</td>
      <td><span class="badge badge-live">${o.status}</span></td>
    </tr>`).join('');
}

document.getElementById('logsFilterSide')?.addEventListener('change', renderOrderLogs);

// ═══════════════════════════════════════════════════════════════
//  ADD ACCOUNT MODAL
// ═══════════════════════════════════════════════════════════════
async function submitAddAccount() {
  const name = document.getElementById('newAccName')?.value?.trim();
  if (!name) { toast('error', 'Validation Error', 'Account name is required'); return; }

  const data = await api('/api/accounts', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({
      name,
      type:       document.getElementById('newAccType')?.value,
      broker:     document.getElementById('newAccBroker')?.value,
      mode:       document.getElementById('newAccMode')?.value,
      balance:    parseFloat(document.getElementById('newAccBalance')?.value || 500000),
      multiplier: parseFloat(document.getElementById('newAccMultiplier')?.value || 1.0),
      api_key:    document.getElementById('newAccApiKey')?.value,
      api_secret: document.getElementById('newAccApiSecret')?.value,
    })
  });

  if (data?.status === 'SUCCESS') {
    toast('success', 'Account Connected', `${name} has been linked successfully`);
    closeModal('accountModal');
    fetchAccounts();
  } else {
    toast('error', 'Connection Failed', data?.message || 'Check credentials');
  }
}

// ═══════════════════════════════════════════════════════════════
//  MODAL HELPERS
// ═══════════════════════════════════════════════════════════════
function openModal(id) {
  document.getElementById(id)?.classList.add('open');
}

function closeModal(id) {
  document.getElementById(id)?.classList.remove('open');
}

// ═══════════════════════════════════════════════════════════════
//  TOAST NOTIFICATION SYSTEM
// ═══════════════════════════════════════════════════════════════
function toast(type, title, message, duration = 4000) {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `
    <div class="toast-dot"></div>
    <div class="toast-content">
      <span class="toast-title">${title}</span>
      <span class="toast-msg">${message}</span>
    </div>`;

  container.appendChild(el);
  setTimeout(() => {
    el.classList.add('fadeOut');
    setTimeout(() => el.remove(), 350);
  }, duration);
}

window.toast = toast;

// ═══════════════════════════════════════════════════════════════
//  BOOT ENGINE
// ═══════════════════════════════════════════════════════════════
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
