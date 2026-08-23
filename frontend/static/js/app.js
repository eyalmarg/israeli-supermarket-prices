const statsBar = document.getElementById("stats-bar");
const searchInput = document.getElementById("search-input");
const searchBtn = document.getElementById("search-btn");
const resultsEl = document.getElementById("results");
const comparePanel = document.getElementById("compare-panel");
const compareTitle = document.getElementById("compare-title");
const compareList = document.getElementById("compare-list");
const closeCompareBtn = document.getElementById("close-compare");

const ILS = (n) => (n === null || n === undefined ? "—" : `₪${Number(n).toFixed(2)}`);

async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    const s = await res.json();
    statsBar.innerHTML =
      `<strong>${s.supermarket_count ?? 0}</strong> רשתות · ` +
      `<strong>${(s.prices_count ?? 0).toLocaleString("he-IL")}</strong> מחירי מוצרים · ` +
      `<strong>${(s.stores_count ?? 0).toLocaleString("he-IL")}</strong> סניפים`;
  } catch (e) {
    statsBar.textContent = "לא ניתן היה לטעון סטטיסטיקות (בדקו שהשרת ומסד הנתונים פעילים)";
  }
}

function renderResults(items) {
  resultsEl.innerHTML = "";
  if (!items.length) {
    resultsEl.innerHTML = `<div class="empty-state">לא נמצאו תוצאות. נסו מילת חיפוש אחרת.</div>`;
    return;
  }
  for (const item of items) {
    const row = document.createElement("div");
    row.className = "result-row";
    row.innerHTML = `
      <div class="receipt-line">
        <span class="name">${item.item_name ?? "מוצר ללא שם"}</span>
        <span class="dots"></span>
        <span class="price">${ILS(item.min_price)}${item.max_price > item.min_price ? " - " + ILS(item.max_price) : ""}</span>
      </div>
      <div class="result-meta">נמכר ב-<span class="best-tag">${item.supermarket_count}</span> רשתות · לחיצה להשוואה מלאה</div>
    `;
    row.addEventListener("click", () => showCompare(item.item_code, item.item_name));
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
    if (res.ok) {
      renderResults(data);
    } else {
      resultsEl.innerHTML = `<div class="error-state">${data.error || "שגיאה בחיפוש"}</div>`;
    }
  } catch (e) {
    resultsEl.innerHTML = `<div class="error-state">שגיאת תקשורת עם השרת</div>`;
  }
}

async function showCompare(itemCode, itemName) {
  comparePanel.classList.remove("hidden");
  compareTitle.textContent = itemName;
  compareList.innerHTML = `<div class="empty-state">טוען השוואה...</div>`;
  comparePanel.scrollIntoView({ behavior: "smooth", block: "start" });

  try {
    const res = await fetch(`/api/compare?item_code=${encodeURIComponent(itemCode)}`);
    const rows = await res.json();
    compareList.innerHTML = "";
    if (!rows.length) {
      compareList.innerHTML = `<div class="empty-state">אין נתוני מחיר זמינים לפריט זה כרגע.</div>`;
      return;
    }
    const minEffective = Math.min(
      ...rows.map((r) => Number(r.discounted_price ?? r.item_price))
    );
    rows.forEach((r) => {
      const effective = Number(r.discounted_price ?? r.item_price);
      const isCheapest = effective === minEffective;
      const div = document.createElement("div");
      div.className = "compare-row" + (isCheapest ? " cheapest" : "");
      div.innerHTML = `
        <span class="store">${r.supermarket_name}${r.city ? ` <span class="city">· ${r.city}</span>` : ""}</span>
        <span class="cdots"></span>
        ${r.discounted_price ? `<span class="promo-badge">מבצע</span>` : ""}
        <span class="cprice">${ILS(effective)}</span>
        ${isCheapest ? `<span class="ribbon">הכי זול</span>` : ""}
      `;
      compareList.appendChild(div);
    });
  } catch (e) {
    compareList.innerHTML = `<div class="error-state">שגיאת תקשורת עם השרת</div>`;
  }
}

closeCompareBtn.addEventListener("click", () => comparePanel.classList.add("hidden"));
searchBtn.addEventListener("click", runSearch);
searchInput.addEventListener("keydown", (e) => { if (e.key === "Enter") runSearch(); });

loadStats();
