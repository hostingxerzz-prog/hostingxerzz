const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();
try {
  tg.setHeaderColor('#0f1320');
  tg.setBackgroundColor('#0f1320');
} catch (e) {}

const INIT = tg.initData;
const STATE = { me: null, view: 'shop' };

// ─────────── API ───────────
async function api(path, method = 'GET', body) {
  const r = await fetch('/api' + path, {
    method,
    headers: { 'Content-Type': 'application/json', 'X-Init-Data': INIT },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || data.error || 'Error');
  return data;
}

// ─────────── Форматтау ───────────
function money(usd) {
  const cur = STATE.me?.lang || 'kk';
  if (cur === 'kk') return Math.round(usd * 470).toLocaleString('ru-RU') + ' ₸';
  if (cur === 'ru') return Math.round(usd * 80.5).toLocaleString('ru-RU') + ' ₽';
  return usd.toFixed(2) + ' USD';
}
function fmt(usd) {
  return (+usd).toFixed(2).replace(/\.00$/, '') + '$';
}

function toast(msg, isErr) {
  const t = document.createElement('div');
  t.className = 'toast';
  if (isErr) t.classList.add('err');
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.classList.add('show'), 10);
  setTimeout(() => {
    t.classList.remove('show');
    setTimeout(() => t.remove(), 300);
  }, 2200);
}

// ─────────── me ───────────
async function loadMe() {
  STATE.me = await api('/me');
  document.getElementById('balance').textContent = fmt(STATE.me.balance);
}

// ─────────── Tabs ───────────
function setTab(t) {
  STATE.view = t;
  document.querySelectorAll('#tabs button').forEach(b =>
    b.classList.toggle('active', b.dataset.tab === t)
  );
  render();
}
document.querySelectorAll('#tabs button').forEach(b => {
  b.onclick = () => setTab(b.dataset.tab);
});

// ─────────── Категориялар ───────────
const CATS = [
  { id: 'NONROOT', label: '🟢 Non-Root' },
  { id: 'ROOT',    label: '🔴 Root' },
  { id: 'PC',      label: '💻 PC' },
  { id: 'IOS',     label: '🍎 iOS' },
  { id: 'OTHER',   label: '📦 Other' },
];

// ─────────── Views ───────────
function viewShop() {
  return `
    <h2>Магазин</h2>
    <div class="cats">
      ${CATS.map(c => `<button class="btn ghost" data-cat="${c.id}">${c.label}</button>`).join('')}
    </div>
    <div class="card" style="margin-top:16px">
      <h3>🔥 Lucky bonus</h3>
      <p class="sub">Күніне 0.01–0.10$ ұтып ал</p>
      <button class="btn ok" onclick="doLucky()">🎁 Алу</button>
    </div>`;
}

async function viewCategory(cat) {
  const { items } = await api('/catalog?cat=' + cat);
  const catLabel = (CATS.find(c => c.id === cat) || {}).label || cat;
  if (!items.length) {
    return `<button class="btn ghost" onclick="setTab('shop')">← Артқа</button>
            <h2 style="margin-top:14px">${catLabel}</h2>
            <p class="center">Қазір бос</p>`;
  }
  return `
    <button class="btn ghost" onclick="setTab('shop')">← Артқа</button>
    <h2 style="margin-top:14px">${catLabel}</h2>
    ${items.map(it => `
      <div class="card">
        <h3>${it.name}</h3>
        ${it.plans.length ? `
        <div class="plans">
          ${it.plans.map((p, i) => `
            <div class="plan ${p.out ? 'oos' : ''}" data-item="${it.name}" data-idx="${i}"
                 data-plan='${JSON.stringify(p)}'>
              <div class="lbl">${p.label}</div>
              <div class="pr">${money(p.price_usd)}</div>
            </div>`).join('')}
        </div>` : `<p class="sub">Жақында қосылады</p>`}
      </div>`).join('')}`;
}

async function viewProfile() {
  const m = STATE.me;
  const { keys } = await api('/mykeys');
  return `
    <h2>Профиль</h2>
    <div class="card">
      <div class="stat"><span>ID</span><b>${m.id}</b></div>
      <div class="stat"><span>Type</span><b>${m.tier}</b></div>
      <div class="stat"><span>Баланс</span><b>${fmt(m.balance)}</b></div>
      <div class="stat"><span>Сатып алынған</span><b>${m.orders}</b></div>
      <div class="stat"><span>Жұмсалды</span><b>${fmt(m.spent)}</b></div>
      <div class="stat"><span>Реферал</span><b>${m.referrals}</b></div>
      <div class="stat"><span>Тіркелген</span><b>${m.created || '-'}</b></div>
    </div>

    <h3 style="margin:16px 0 8px">🔑 Менің кілттерім</h3>
    <div class="card">
      ${keys.length ? keys.map(k => `
        <div style="padding:10px 0;border-bottom:1px solid #232a42">
          <b>${k.product}</b> — <span style="color:var(--muted)">${k.label}</span>
          <div class="key">${k.license}</div>
          <button class="btn ghost" style="margin-top:6px;font-size:12px;padding:8px"
            onclick="resetKey('${k.license.replace(/'/g, "\\'")}')">
            ♻️ Reset (${k.resets}/3)
          </button>
        </div>`).join('') : '<p class="sub">Әзірге кілт жоқ</p>'}
    </div>`;
}

function viewTopup() {
  return `
    <h2>Баланс толтыру</h2>
    <div class="card">
      <label style="display:block;margin-bottom:8px;color:var(--muted);font-size:13px">
        Сома (1–100 USD)
      </label>
      <input class="input" id="amt" type="number" min="1" max="100" value="5">
      <button class="btn ok" onclick="doTopup('binance')">💳 Binance арқылы</button>
      <button class="btn ok" onclick="doTopup('kaspi')">💳 Kaspi арқылы</button>
    </div>
    <div class="card">
      <h3>ℹ️ Қалай жұмыс істейді?</h3>
      <p class="sub">
        1. Соманы енгіз<br>
        2. Төлем жүйесін таңда<br>
        3. Чекті ботқа админге жібер<br>
        4. Админ растаған соң баланс толады
      </p>
    </div>`;
}

async function viewMore() {
  const r = await api('/referral');
  return `
    <h2>Тағы</h2>
    <div class="card">
      <h3>🎁 Lucky bonus</h3>
      <p class="sub">Күніне 0.01–0.10$ ұтып ал</p>
      <button class="btn ok" onclick="doLucky()">Алу</button>
    </div>

    <div class="card">
      <h3>👥 Реферал</h3>
      <p class="sub">Шақырылған: <b>${r.referrals}</b> • Табыс: <b>${fmt(r.earned)}</b></p>
      <input class="input" readonly value="${r.link}">
      <button class="btn" onclick="copyLink('${r.link}')">📋 Көшіру</button>
    </div>

    <div class="card">
      <h3>🔑 Реселлер болу</h3>
      <p class="sub">Админ берген логин/парольді енгіз</p>
      <input class="input" id="rl" placeholder="Login">
      <input class="input" id="rp" type="password" placeholder="Password">
      <button class="btn" onclick="becomeReseller()">Активтеу</button>
    </div>

    <div class="card">
      <h3>🌐 Тіл</h3>
      <div style="display:flex;gap:8px;margin-top:8px">
        <button class="btn ghost" onclick="setLang('kk')">Қазақша</button>
        <button class="btn ghost" onclick="setLang('ru')">Русский</button>
        <button class="btn ghost" onclick="setLang('en')">English</button>
      </div>
    </div>`;
}

// ─────────── Render ───────────
async function render() {
  const el = document.getElementById('view');
  try {
    if (STATE.view === 'shop')          el.innerHTML = viewShop();
    else if (STATE.view === 'profile')  el.innerHTML = await viewProfile();
    else if (STATE.view === 'topup')    el.innerHTML = viewTopup();
    else if (STATE.view === 'more')     el.innerHTML = await viewMore();
    else if (STATE.view.startsWith('cat:')) {
      el.innerHTML = '<p class="center">⏳</p>';
      el.innerHTML = await viewCategory(STATE.view.split(':')[1]);
    }

    // Bind events
    el.querySelectorAll('[data-cat]').forEach(b => {
      b.onclick = () => { STATE.view = 'cat:' + b.dataset.cat; render(); };
    });
    el.querySelectorAll('[data-plan]').forEach(p => {
      p.onclick = () => openBuy(JSON.parse(p.dataset.plan));
    });
  } catch (e) {
    el.innerHTML = `<p class="center">❌ ${e.message}</p>`;
  }
}

// ─────────── Actions ───────────
async function openBuy(plan) {
  if (plan.out) return toast('❌ Қорда жоқ', true);
  const max = plan.max_qty || 1;
  const qty = parseInt(prompt(`Саны (1–${max}):`, '1') || '0');
  if (!qty || qty < 1 || qty > max) return toast('Қате сан', true);

  const total = plan.price_usd * qty;
  if (!confirm(`${plan.label} × ${qty}\nБаға: ${money(total)}\n\nРастайсың ба?`)) return;

  let android_id = null;
  if (plan.android) {
    android_id = prompt('Android ID (6–64 таңба):');
    if (!android_id) return toast('Android ID керек', true);
  }
  await doBuy(plan.variant_id, qty, android_id);
}

async function doBuy(variant_id, qty, android_id) {
  try {
    const r = await api('/buy', 'POST', { variant_id, qty, android_id });
    await loadMe();
    let txt = '✅ Сатып алынды!\n\n';
    if (r.keys.length) txt += r.keys.map(k => '🔑 ' + k).join('\n');
    else txt += JSON.stringify(r.raw);
    alert(txt);
    render();
  } catch (e) {
    toast('❌ ' + e.message, true);
  }
}

async function doTopup(method) {
  const amt = parseFloat(document.getElementById('amt').value);
  if (!(amt >= 1 && amt <= 100)) return toast('Сома 1–100 USD', true);
  try {
    const r = await api('/topup', 'POST', { amount: amt, method });
    let txt = `🧾 Төлем #${r.order_id}\n\n`;
    if (method === 'binance') {
      txt += `Binance ID: ${r.details.binance_id}\nСома: ${amt} USD\n\n`;
    } else {
      txt += `Телефон: ${r.details.phone}\nАты: ${r.details.name}\nСома: ${r.details.kzt} ₸\n\n`;
    }
    txt += 'Төлемнен кейін чекті боттағы админге жібер.';
    alert(txt);
  } catch (e) {
    toast(e.message, true);
  }
}

async function doLucky() {
  try {
    const r = await api('/lucky', 'POST', {});
    await loadMe();
    toast(`🎁 +$${r.amount.toFixed(2)}`);
    render();
  } catch (e) {
    toast(e.message, true);
  }
}

async function setLang(lang) {
  try {
    await api('/lang', 'POST', { lang });
    await loadMe();
    toast('✅ Тіл өзгертілді');
    render();
  } catch (e) {
    toast(e.message, true);
  }
}

async function becomeReseller() {
  const login = document.getElementById('rl').value.trim();
  const password = document.getElementById('rp').value.trim();
  if (!login || !password) return toast('Толық енгіз', true);
  try {
    await api('/reseller', 'POST', { login, password });
    await loadMe();
    toast('✅ Реселлер активтелді!');
    render();
  } catch (e) {
    toast(e.message, true);
  }
}

async function resetKey(key) {
  if (!confirm('Бұл кілтті reset жасайсың ба?')) return;
  try {
    const r = await api('/reset', 'POST', { key });
    toast(`✅ Reset. Қалғаны: ${r.left}`);
    render();
  } catch (e) {
    toast(e.message, true);
  }
}

function copyLink(t) {
  navigator.clipboard.writeText(t);
  toast('✅ Көшірілді');
}

// ─────────── Boot ───────────
(async () => {
  try {
    await loadMe();
    setTab('shop');
  } catch (e) {
    document.getElementById('view').innerHTML =
      `<p class="center">❌ ${e.message}<br><br>Боттан аш (Mini App арқылы)</p>`;
  }
})();