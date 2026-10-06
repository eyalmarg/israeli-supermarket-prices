// כל המחירים באתר הם מחירים רגילים (ללא מבצעים).
// הנתונים נקראים מ-Supabase דרך פונקציות SQL (ראו db/schema.sql), עם מפתח ציבורי לקריאה בלבד.
const $ = (id) => document.getElementById(id);

const statsBar = $("stats-bar");
const searchInput = $("search-input");
const resultsEl = $("results");
const productPanel = $("product-panel");
const productBody = $("product-body");
const basketPanel = $("basket-panel");
const basketItemsEl = $("basket-items");
const basketResultsEl = $("basket-results");
const basketCountEl = $("basket-count");

const BASKET_KEY = "mechir-agala-basket";

async function rpc(fn, args) {
  const { SUPABASE_URL, SUPABASE_KEY } = window.APP_CONFIG;
  const res = await fetch(`${SUPABASE_URL}/rest/v1/rpc/${fn}`, {
    method: "POST",
    headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify(args || {}),
  });
  if (!res.ok) throw new Error(`${fn}: ${res.status}`);
  return res.json();
}

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

const storesLabel = (n) => (Number(n) === 1 ? "סניף אחד" : `${Number(n).toLocaleString("he-IL")} סניפים`);

function storage(fn, fallback) {
  try { return fn(); } catch (e) { return fallback; }
}

const errorBox = (msg) => `<div class="error-state">${esc(msg)}</div>`;

// ---------------- Stats ----------------

async function loadStats() {
  try {
    const s = await rpc("site_stats");
    if (!s.products_count) {
      statsBar.textContent = "המאגר עדיין ריק — הנתונים ייטענו בעדכון היומי הקרוב";
      return;
    }
    statsBar.innerHTML =
      `<strong>${esc(s.supermarket_count)}</strong> רשתות · ` +
      `<strong>${esc(Number(s.stores_count).toLocaleString("he-IL"))}</strong> סניפים · ` +
      `<strong>${esc(Number(s.products_count).toLocaleString("he-IL"))}</strong> מוצרים` +
      (s.last_update ? ` · עודכן ${esc(fmtDate(s.last_update))}` : "");
    if (s.chains.length) {
      $("chains-list").textContent =
        "רשתות במאגר: " + s.chains.map((c) => `${c.supermarket_name} (${fmtDate(c.data_date)})`).join(" · ");
    }
  } catch (e) {
    statsBar.textContent = "לא ניתן לטעון נתונים כרגע";
  }
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
    resultsEl.innerHTML = errorBox("הקלידו לפחות 2 תווים");
    return;
  }
  resultsEl.innerHTML = `<div class="empty-state">מחפש...</div>`;
  try {
    renderResults(await rpc("search_products", { q: term }));
  } catch (e) {
    resultsEl.innerHTML = errorBox("שגיאה בחיפוש, נסו שוב");
  }
}

// ---------------- Product comparison ----------------

async function showProduct(itemCode) {
  basketPanel.classList.add("hidden");
  productPanel.classList.remove("hidden");
  productBody.innerHTML = `<div class="empty-state">טוען השוואה...</div>`;
  productPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  try {
    const data = await rpc("product_detail", { code: itemCode });
    if (!data) {
      productBody.innerHTML = errorBox("המוצר לא נמצא");
      return;
    }
    renderProduct(data.product, data.chains);
  } catch (e) {
    productBody.innerHTML = errorBox("שגיאה בטעינת ההשוואה, נסו שוב");
  }
}

function renderProduct(p, chains) {
  const inBasket = basket.some((b) => b.item_code === p.item_code);
  const cheapest = chains.length ? Math.min(...chains.map((c) => c.median_price)) : null;

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
    <h3 class="section-title">השוואה לפי רשת</h3>
    <p class="hint">המחיר בסניפים של כל רשת: הזול ביותר, החציוני (הסניף ה"טיפוסי") והיקר ביותר. ממוין לפי המחיר החציוני.</p>
    <div class="chain-table" role="table">
      <div class="chain-row head" role="row">
        <span role="columnheader">רשת</span>
        <span role="columnheader">חציון</span>
        <span role="columnheader">הכי זול</span>
        <span role="columnheader">הכי יקר</span>
      </div>`;
  for (const c of chains) {
    const best = c.median_price === cheapest;
    html += `
      <div class="chain-row${best ? " cheapest" : ""}" role="row">
        <span class="chain-name" role="cell">${esc(c.supermarket_name)}${best ? ` <span class="ribbon">הכי זול</span>` : ""}
          <small>${esc(storesLabel(c.store_count))}</small></span>
        <span class="num strong" role="cell">${ILS(c.median_price)}</span>
        <span class="num" role="cell">${ILS(c.min_price)}</span>
        <span class="num" role="cell">${ILS(c.max_price)}</span>
      </div>`;
  }
  html += `</div>`;
  productBody.innerHTML = html;

  const btn = $("add-to-basket");
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
    const rows = await rpc("compare_basket", {
      items: basket.map(({ item_code, qty }) => ({ item_code, qty })),
    });
    renderBasketResults(rows);
  } catch (e) {
    basketResultsEl.innerHTML = errorBox("שגיאה בהשוואת הסל, נסו שוב");
  }
}

function renderBasketResults(rows) {
  if (!rows.length) {
    basketResultsEl.innerHTML = `<div class="empty-state">לא נמצאו רשתות שמוכרות את המוצרים בסל.</div>`;
    return;
  }
  const total = basket.length;
  const complete = rows.filter((r) => r.found_count === total);
  const cheapestComplete = complete.length ? Math.min(...complete.map((r) => r.total)) : null;

  let html = `<h3 class="section-title">מחיר הסל בכל רשת</h3>
    <p class="hint">המחיר הראשי הוא בסניף טיפוסי של הרשת (חציון). מתחתיו — אם קונים הכול במחיר הזול ביותר שיש ברשת. מחירים רגילים, ללא מבצעים.</p>`;
  for (const r of rows) {
    const isComplete = r.found_count === total;
    const best = isComplete && r.total === cheapestComplete;
    const prices = r.item_prices || {};
    const missing = basket.filter((b) => !(b.item_code in prices));
    html += `
      <details class="basket-result${best ? " cheapest" : ""}${isComplete ? "" : " partial"}">
        <summary>
          <span class="store">${esc(r.supermarket_name)}${best ? ` <span class="ribbon">הכי זול</span>` : ""}
            <span class="city">בסניף הזול ברשת: ${ILS(r.total_min)}</span></span>
          <span class="cdots"></span>
          <span class="found">${esc(r.found_count)}/${esc(total)} מוצרים</span>
          <span class="cprice">${ILS(r.total)}</span>
        </summary>
        <div class="basket-breakdown">
          ${basket
            .filter((b) => b.item_code in prices)
            .map((b) => `<div class="line"><span>${esc(b.item_name)} × ${esc(b.qty)}</span><span>${ILS(prices[b.item_code].median * b.qty)}</span></div>`)
            .join("")}
          ${missing.length ? `<div class="missing">לא נמכר ברשת: ${missing.map((b) => esc(b.item_name)).join(", ")}</div>` : ""}
        </div>
      </details>`;
  }
  basketResultsEl.innerHTML = html;
}

// ---------------- Wiring ----------------

$("search-btn").addEventListener("click", runSearch);
searchInput.addEventListener("keydown", (e) => { if (e.key === "Enter") runSearch(); });
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
