// כל המחירים באתר הם מחירים רגילים (ללא מבצעים).
const $ = (id) => document.getElementById(id);

const statsBar = $("stats-bar");
const searchInput = $("search-input");
const citySelect = $("city-select");
const resultsEl = $("results");
const productPanel = $("product-panel");
const productBody = $("product-body");
const basketPanel = $("basket-panel");
const basketItemsEl = $("basket-items");
const basketResultsEl = $("basket-results");
const basketCountEl = $("basket-count");

const BASKET_KEY = "mechir-agala-basket";
const CITY_KEY = "mechir-agala-city";

// הנתונים מגיעים מקבצים חיצוניים של הרשתות — תמיד מבריחים לפני הצגה
const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const ILS = (n) => (n === null || n === undefined ? "—" : `₪${Number(n).toFixed(2)}`);

const fmtDate = (d) => {
  if (!d) return "";
  const dt = new Date(d);
  return isNaN(dt) ? "" : dt.toLocaleDateString("he-IL");
};

const sizeLabel = (p) => {
  if (p.is_weighted) return "מחיר לק״ג";
  if (!p.quantity || !p.unit_qty) return "";
  return `${Number(p.quantity).toLocaleString("he-IL")} ${p.unit_qty}`;
};

const storesLabel = (n) => (Number(n) === 1 ? "סניף אחד" : `${n} סניפים`);

const city = () => citySelect.value || null;

function storage(fn, fallback) {
  try { return fn(); } catch (e) { return fallback; }
}

// ---------------- Stats / cities ----------------

async function loadStats() {
  try {
    const s = await (await fetch("/api/stats")).json();
    statsBar.innerHTML =
      `<strong>${esc(s.supermarket_count ?? 0)}</strong> רשתות · ` +
      `<strong>${esc((s.stores_count ?? 0).toLocaleString("he-IL"))}</strong> סניפים · ` +
      `<strong>${esc((s.products_count ?? 0).toLocaleString("he-IL"))}</strong> מוצרים` +
      (s.last_update ? ` · עודכן ${esc(fmtDate(s.last_update))}` : "");
  } catch (e) {
    statsBar.textContent = "לא ניתן לטעון נתונים (בדקו שהשרת ומסד הנתונים פעילים)";
  }
}

async function loadCities() {
  try {
    const cities = await (await fetch("/api/cities")).json();
    for (const c of cities) {
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = c;
      citySelect.appendChild(opt);
    }
    const saved = storage(() => localStorage.getItem(CITY_KEY), null);
    if (saved && cities.includes(saved)) citySelect.value = saved;
  } catch (e) { /* לא קריטי */ }
}

async function loadChains() {
  try {
    const chains = await (await fetch("/api/supermarkets")).json();
    if (chains.length) {
      $("chains-list").textContent = "רשתות במאגר: " + chains.map((c) => c.supermarket_name).join(" · ");
    }
  } catch (e) { /* לא קריטי */ }
}

// ---------------- Search ----------------

function renderResults(items) {
  if (!items.length) {
    resultsEl.innerHTML = `<div class="empty-state">לא נמצאו מוצרים. נסו מילת חיפוש אחרת או ברקוד.</div>`;
    return;
  }
  resultsEl.innerHTML = "";
  for (const item of items) {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "result-row";
    const range = item.max_price > item.min_price ? `${ILS(item.min_price)} – ${ILS(item.max_price)}` : ILS(item.min_price);
    row.innerHTML = `
      <div class="receipt-line">
        <span class="name">${esc(item.item_name || "מוצר ללא שם")}</span>
        <span class="dots"></span>
        <span class="price">${esc(range)}</span>
      </div>
      <div class="result-meta">
        ${item.manufacturer_name ? `${esc(item.manufacturer_name)} · ` : ""}${sizeLabel(item) ? `${esc(sizeLabel(item))} · ` : ""}
        נמכר ב-<span class="best-tag">${esc(item.chain_count)}</span> רשתות (${esc(storesLabel(item.store_count))})
      </div>`;
    row.addEventListener("click", () => showProduct(item.item_code));
    resultsEl.appendChild(row);
  }
}

async function runSearch() {
  const term = searchInput.value.trim();
  if (term.length < 2) {
    resultsEl.innerHTML = `<div class="error-state">הקלידו לפחות 2 תווים</div>`;
    return;
  }
  resultsEl.innerHTML = `<div class="empty-state">מחפש...</div>`;
  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(term)}`);
    const data = await res.json();
    if (res.ok) renderResults(data);
    else resultsEl.innerHTML = `<div class="error-state">${esc(data.error || "שגיאה בחיפוש")}</div>`;
  } catch (e) {
    resultsEl.innerHTML = `<div class="error-state">שגיאת תקשורת עם השרת</div>`;
  }
}

// ---------------- Product comparison ----------------

let currentProductCode = null;

async function showProduct(itemCode) {
  currentProductCode = itemCode;
  basketPanel.classList.add("hidden");
  productPanel.classList.remove("hidden");
  productBody.innerHTML = `<div class="empty-state">טוען השוואה...</div>`;
  productPanel.scrollIntoView({ behavior: "smooth", block: "start" });

  const params = new URLSearchParams();
  if (city()) params.set("city", city());
  try {
    const res = await fetch(`/api/products/${encodeURIComponent(itemCode)}?${params}`);
    const p = await res.json();
    if (!res.ok) {
      productBody.innerHTML = `<div class="error-state">${esc(p.error || "שגיאה")}</div>`;
      return;
    }
    renderProduct(p);
  } catch (e) {
    productBody.innerHTML = `<div class="error-state">שגיאת תקשורת עם השרת</div>`;
  }
}

function renderProduct(p) {
  const inBasket = basket.some((b) => b.item_code === p.item_code);
  const where = city() ? `ב${esc(city())}` : "בכל הארץ";
  const cheapest = p.chains.length ? p.chains[0].min_price : null;

  let html = `
    <h2 class="panel-title">${esc(p.item_name)}</h2>
    <p class="product-sub">
      ${p.manufacturer_name ? esc(p.manufacturer_name) + " · " : ""}${sizeLabel(p) ? esc(sizeLabel(p)) + " · " : ""}ברקוד ${esc(p.item_code)}
    </p>
    <div class="product-actions">
      <button type="button" class="primary-btn" id="add-to-basket" ${inBasket ? "disabled" : ""}>
        ${inBasket ? "✓ בסל" : "+ הוספה לסל"}
      </button>
    </div>
    <h3 class="section-title">השוואה לפי רשת ${where}</h3>`;

  if (!p.chains.length) {
    html += `<div class="empty-state">אין מחירים למוצר הזה ${where}.</div>`;
    productBody.innerHTML = html;
    bindAddToBasket(p);
    return;
  }

  html += `<div class="chain-table" role="table">
    <div class="chain-row head" role="row">
      <span role="columnheader">רשת</span>
      <span role="columnheader">הכי זול</span>
      <span role="columnheader">חציון</span>
      <span role="columnheader">הכי יקר</span>
    </div>`;
  for (const c of p.chains) {
    const best = c.min_price === cheapest;
    html += `
      <div class="chain-row${best ? " cheapest" : ""}" role="row">
        <span class="chain-name" role="cell">${esc(c.supermarket_name)}${best ? ` <span class="ribbon">הכי זול</span>` : ""}
          <small>${esc(storesLabel(c.store_count))}</small></span>
        <span class="num strong" role="cell">${ILS(c.min_price)}</span>
        <span class="num" role="cell">${ILS(c.median_price)}</span>
        <span class="num" role="cell">${ILS(c.max_price)}</span>
      </div>`;
  }
  html += `</div>`;

  html += `<details class="stores-details">
    <summary>כל הסניפים (${esc(p.stores.length)}${p.stores.length >= 500 ? "+" : ""}) ממוינים לפי מחיר</summary>
    <div class="store-list">`;
  for (const s of p.stores) {
    const place = [s.store_name, s.address, s.city].filter(Boolean).join(", ");
    html += `
      <div class="store-row">
        <span class="store">${esc(s.supermarket_name)}${s.sub_chain_name && s.sub_chain_name !== s.supermarket_name ? ` <small>(${esc(s.sub_chain_name)})</small>` : ""}
          <span class="city">${esc(place || `סניף ${s.store_id}`)}</span></span>
        <span class="cdots"></span>
        <span class="cprice">${ILS(s.item_price)}</span>
      </div>`;
  }
  html += `</div></details>`;

  productBody.innerHTML = html;
  bindAddToBasket(p);
}

function bindAddToBasket(p) {
  const btn = $("add-to-basket");
  if (!btn) return;
  btn.addEventListener("click", () => {
    addToBasket(p);
    btn.disabled = true;
    btn.textContent = "✓ בסל";
  });
}

// ---------------- Basket ----------------

let basket = storage(() => JSON.parse(localStorage.getItem(BASKET_KEY) || "[]"), []);
if (!Array.isArray(basket)) basket = [];

function saveBasket() {
  storage(() => localStorage.setItem(BASKET_KEY, JSON.stringify(basket)));
  basketCountEl.textContent = basket.length;
}

function addToBasket(p) {
  if (basket.some((b) => b.item_code === p.item_code)) return;
  basket.push({ item_code: p.item_code, item_name: p.item_name, is_weighted: !!p.is_weighted, qty: 1 });
  saveBasket();
}

function renderBasket() {
  basketResultsEl.innerHTML = "";
  if (!basket.length) {
    basketItemsEl.innerHTML = `<div class="empty-state">הסל ריק. חפשו מוצר ולחצו "הוספה לסל".</div>`;
    $("basket-compare").disabled = true;
    return;
  }
  $("basket-compare").disabled = false;
  basketItemsEl.innerHTML = "";
  basket.forEach((b, idx) => {
    const row = document.createElement("div");
    row.className = "basket-row";
    row.innerHTML = `
      <span class="basket-name">${esc(b.item_name)}</span>
      <label class="qty">
        <span class="sr-only">כמות</span>
        <input type="number" min="${b.is_weighted ? "0.1" : "1"}" step="${b.is_weighted ? "0.1" : "1"}" value="${esc(b.qty)}">
        <span>${b.is_weighted ? "ק״ג" : "יח׳"}</span>
      </label>
      <button type="button" class="link-btn remove" aria-label="הסרה">✕</button>`;
    row.querySelector("input").addEventListener("change", (e) => {
      const v = parseFloat(e.target.value);
      b.qty = v > 0 ? v : 1;
      e.target.value = b.qty;
      saveBasket();
    });
    row.querySelector(".remove").addEventListener("click", () => {
      basket.splice(idx, 1);
      saveBasket();
      renderBasket();
    });
    basketItemsEl.appendChild(row);
  });
}

function openBasket() {
  productPanel.classList.add("hidden");
  basketPanel.classList.remove("hidden");
  renderBasket();
  basketPanel.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function compareBasket() {
  basketResultsEl.innerHTML = `<div class="empty-state">משווה...</div>`;
  try {
    const res = await fetch("/api/basket", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items: basket.map(({ item_code, qty }) => ({ item_code, qty })), city: city() }),
    });
    const rows = await res.json();
    if (!res.ok) {
      basketResultsEl.innerHTML = `<div class="error-state">${esc(rows.error || "שגיאה")}</div>`;
      return;
    }
    renderBasketResults(rows);
  } catch (e) {
    basketResultsEl.innerHTML = `<div class="error-state">שגיאת תקשורת עם השרת</div>`;
  }
}

function renderBasketResults(rows) {
  const where = city() ? `ב${esc(city())}` : "בכל הארץ";
  if (!rows.length) {
    basketResultsEl.innerHTML = `<div class="empty-state">לא נמצאו סניפים ${where} שמוכרים את המוצרים בסל.</div>`;
    return;
  }
  const total = basket.length;
  const complete = rows.filter((r) => r.found_count === total);
  const cheapestComplete = complete.length ? Math.min(...complete.map((r) => r.total)) : null;

  let html = `<h3 class="section-title">הסניף הזול ביותר בכל רשת ${where}</h3>
    <p class="hint">לכל רשת נבחר הסניף שיש בו הכי הרבה מהמוצרים בסל, ומביניהם הזול ביותר. מחירים רגילים, ללא מבצעים.</p>`;
  for (const r of rows) {
    const isComplete = r.found_count === total;
    const best = isComplete && r.total === cheapestComplete;
    const prices = r.item_prices || {};
    const missing = basket.filter((b) => !(b.item_code in prices));
    const place = [r.store_name, r.city].filter(Boolean).join(", ") || `סניף ${r.store_id}`;
    html += `
      <details class="basket-result${best ? " cheapest" : ""}${isComplete ? "" : " partial"}">
        <summary>
          <span class="store">${esc(r.supermarket_name)}${best ? ` <span class="ribbon">הכי זול</span>` : ""}
            <span class="city">${esc(place)}</span></span>
          <span class="cdots"></span>
          <span class="found">${esc(r.found_count)}/${esc(total)} מוצרים</span>
          <span class="cprice">${ILS(r.total)}</span>
        </summary>
        <div class="basket-breakdown">
          ${r.address ? `<div class="hint">${esc(r.address)}</div>` : ""}
          ${basket
            .filter((b) => b.item_code in prices)
            .map((b) => `<div class="line"><span>${esc(b.item_name)} × ${esc(b.qty)}</span><span>${ILS(prices[b.item_code] * b.qty)}</span></div>`)
            .join("")}
          ${missing.length ? `<div class="missing">חסר בסניף: ${missing.map((b) => esc(b.item_name)).join(", ")}</div>` : ""}
        </div>
      </details>`;
  }
  basketResultsEl.innerHTML = html;
}

// ---------------- Wiring ----------------

$("search-btn").addEventListener("click", runSearch);
searchInput.addEventListener("keydown", (e) => { if (e.key === "Enter") runSearch(); });
citySelect.addEventListener("change", () => {
  storage(() => localStorage.setItem(CITY_KEY, citySelect.value));
  if (!productPanel.classList.contains("hidden") && currentProductCode) showProduct(currentProductCode);
  if (!basketPanel.classList.contains("hidden") && basketResultsEl.innerHTML) compareBasket();
});
document.querySelectorAll("[data-close]").forEach((btn) =>
  btn.addEventListener("click", () => $(btn.dataset.close).classList.add("hidden"))
);
$("basket-fab").addEventListener("click", openBasket);
$("basket-compare").addEventListener("click", compareBasket);
$("basket-clear").addEventListener("click", () => {
  basket = [];
  saveBasket();
  renderBasket();
});

saveBasket();
loadStats();
loadCities();
loadChains();
