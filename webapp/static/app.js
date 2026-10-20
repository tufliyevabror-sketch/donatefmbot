/* ================= Donate FM Mini App ================= */
const tg = window.Telegram?.WebApp;

let WEBAPP_I18N = {};
let currentLang = "uz";

function wt(key, ...args) {
    const dict = WEBAPP_I18N[currentLang] || WEBAPP_I18N["uz"] || {};
    let text = dict[key] || WEBAPP_I18N["uz"]?.[key] || key;
    args.forEach((arg, i) => { text = text.replace("{" + i + "}", arg); });
    return text;
}

function setWebappI18n(lang, data) {
    currentLang = lang;
    WEBAPP_I18N = data || {};
}

function hydrateI18n(root) {
    const scope = root || document;
    scope.querySelectorAll("[data-i18n]").forEach((el) => {
        const [key, ...args] = el.getAttribute("data-i18n").split(":");
        el.textContent = wt(key, ...args);
    });
    scope.querySelectorAll("[data-i18n-html]").forEach((el) => {
        const [key, ...args] = el.getAttribute("data-i18n-html").split(":");
        el.innerHTML = wt(key, ...args);
    });
    scope.querySelectorAll("[data-i18n-ph]").forEach((el) => {
        el.placeholder = wt(el.getAttribute("data-i18n-ph"));
    });
    scope.querySelectorAll("[data-i18n-title]").forEach((el) => {
        el.title = wt(el.getAttribute("data-i18n-title"));
    });
    if (typeof renderBonus === "function") renderBonus();
}

function stLabel(code) {
    const map = {
        "kutilmoqda": "st_pending", "tasdiqlandi": "st_ok",
        "rad_etildi": "st_rejected", "bekor_qilindi": "st_cancelled",
        "qaytarildi": "st_refunded", "to'lov_kutilmoqda": "st_waitpay",
        "to'landi": "st_paid",
    };
    return wt(map[code] || "st_pending");
}

let state = {
  user: null,
  games: [],
  card_number: "",
  card_uzcard: "",
  card_humo: "",
  card_tbc: "",
  card_uzum: "",
  card_name: "",
  cardsList: [],
  currentGame: null,
  canVerify: false,
  savedIds: [],
  playerId: "",
  verifiedName: null,
  selectedPkg: null,
  payMethod: "stars",
  topupAmount: 0,
  historyTab: "orders",
  backStack: [],
  activeCat: "all",
  inviteLink: "",
  botUsername: "",
  adminUsername: "",
  supportUsername: "",
  supportPhone: "",
  supportEmail: "",
  payWindowSecs: 300,
  minTopup: 3000,
  isAdmin: false,
  adminTab: "dash",
  adminOrderFilter: "kutilmoqda",
  adminPayAll: false,
  homeFilter: "all",
  favorites: [],
  cart: [],
  historyOrders: [],
  unreadNotifs: 0,
  theme: "dark",
  dailyBonus: { last: 0, amount: 5000 },
  gameIsFav: false,
  homeGameFilter: "all",
  pkgSearch: "",
  pkgSort: "default",
  pkgMin: "",
  pkgMax: "",
};

let mainButtonAction = null;

const fmt = (v) => Number(v || 0).toLocaleString("ru-RU").replace(/,/g, " ");

function hideSplash() {
  const s = document.getElementById("splash");
  if (s) { s.classList.add("hide"); setTimeout(() => s.remove(), 450); }
}

const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[c]);

/* ---------------- THEME ---------------- */
function systemTheme() {
  try {
    const cs = tg && tg.colorScheme;
    if (cs === "light" || cs === "dark") return cs;
    return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  } catch (e) {
    return "dark";
  }
}

function applyTheme(theme, persist) {
  if (theme === "auto") state.themeMode = "auto";
  else state.themeMode = theme === "light" ? "light" : "dark";
  const resolved = state.themeMode === "auto" ? systemTheme() : state.themeMode;
  state.theme = resolved === "light" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", state.theme);
  try { localStorage.setItem("gs_theme", state.theme); } catch (e) {}
  try { localStorage.setItem("gs_theme_mode", state.themeMode); } catch (e) {}
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.content = state.theme === "light" ? "#f4f7fb" : "#0e1621";
  const cs = document.querySelector('meta[name="color-scheme"]');
  if (cs) cs.content = state.theme;
  try { tg?.setHeaderColor?.(state.theme === "light" ? "#f4f7fb" : "#0e1621"); } catch (e) {}
  try { tg?.setBackgroundColor?.(state.theme === "light" ? "#f4f7fb" : "#0e1621"); } catch (e) {}
  const ta = document.getElementById("theme-auto");
  if (ta) ta.classList.toggle("active", state.themeMode === "auto");
  if (persist && state.user) api("/api/save_theme", { theme: state.theme });
  applyTgThemeParams();
}

function applyTgThemeParams() {
  const root = document.documentElement;
  if (tg && tg.themeParams && state.themeMode === "auto") {
    const p = tg.themeParams;
    if (p.bg_color) root.style.setProperty("--bg", p.bg_color);
    if (p.secondary_bg_color) root.style.setProperty("--card", p.secondary_bg_color);
    root.setAttribute("data-tg", "1");
  } else {
    root.style.removeProperty("--bg");
    root.style.removeProperty("--card");
    root.removeAttribute("data-tg");
  }
}

function toggleTheme() {
  applyTheme(state.theme === "dark" ? "light" : "dark", true);
  tg?.HapticFeedback?.selectionChanged();
  toast(state.theme === "light" ? wt("light_mode") : wt("dark_mode"));
}

function setThemeAuto() {
  applyTheme("auto", true);
  tg?.HapticFeedback?.selectionChanged?.();
  toast("🖥 " + wt("theme_auto") + " — " + wt(state.theme + "_mode"));
}

try {
  window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", () => {
    if (state.themeMode === "auto") applyTheme("auto", false);
  });
} catch (e) {}

/* ---------------- COUNT-UP ---------------- */
function countUp(el, to, suffix = "") {
  if (!el) return;
  const from = Number(String(el.textContent).replace(/[^\d.-]/g, "")) || 0;
  const dur = 650;
  const start = performance.now();
  el.classList.remove("count-animate");
  void el.offsetWidth;
  el.classList.add("count-animate");
  function step(t) {
    const p = Math.min(1, (t - start) / dur);
    const ease = 1 - Math.pow(1 - p, 3);
    const val = Math.round(from + (to - from) * ease);
    el.textContent = fmt(val) + suffix;
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

/* ---------------- HAPTICS ---------------- */
function haptic(type = "light") {
  try {
    if (type === "success") tg?.HapticFeedback?.notificationOccurred("success");
    else if (type === "error") tg?.HapticFeedback?.notificationOccurred("error");
    else if (type === "selection") tg?.HapticFeedback?.selectionChanged();
    else tg?.HapticFeedback?.impactOccurred?.("light");
  } catch (e) {}
}

function tgPopup(title, message, buttons) {
  return new Promise((resolve) => {
    if (tg && tg.showPopup) {
      tg.showPopup(
        {
          title: title || "",
          message: message || "",
          buttons: buttons || [{ id: "ok", type: "default", text: "OK" }],
        },
        (id) => resolve(id)
      );
    } else if (tg && tg.showAlert) {
      tg.showAlert([title, message].filter(Boolean).join("\n"));
      resolve("ok");
    } else {
      window.alert([title, message].filter(Boolean).join("\n"));
      resolve("ok");
    }
  });
}

/* ---------------- LOTTIE ---------------- */
const LOTTIE_URLS = {
  loading: "/static/lottie/loading.json",
  success: "/static/lottie/success.json",
  empty: "/static/lottie/empty.json",
};

function playLottie(el, name, opts = {}) {
  if (!el || typeof lottie === "undefined") return null;
  try {
    return lottie.loadAnimation({
      container: el,
      renderer: "svg",
      loop: opts.loop !== false,
      autoplay: true,
      path: LOTTIE_URLS[name] || name,
    });
  } catch (e) {
    return null;
  }
}

function lottieSuccess() {
  if (typeof lottie === "undefined") return;
  const el = document.createElement("div");
  el.className = "lottie-success";
  document.body.appendChild(el);
  const a = playLottie(el, "success", { loop: false });
  if (!a) { el.remove(); return; }
  try { a.addEventListener("complete", () => el.remove()); } catch (e) {}
  setTimeout(() => el.remove(), 1800);
}

function syncTgChrome() {
  const bb = tg && tg.BackButton;
  if (!bb) return;
  const v = activeViewId();
  const isTab = v === "view-home" || v === "view-history" || v === "view-settings" || v === "view-admin";
  const show = !!topPage() || !isTab;
  try { show ? bb.show() : bb.hide(); } catch (e) {}
}

function syncMainButton() {
  const mb = tg && tg.MainButton;
  if (!mb) return;
  const page = topPage() ? topPage().id : null;
  let show = false;
  if (page === "pay-sheet") {
    mainButtonAction = () => chooseMethod("balance");
    try { mb.setParams({ text: "💠 " + wt("pay_with_bal") }); } catch (e) {}
    show = true;
  } else if (page === "cart-sheet" && state.cart.length) {
    const total = state.cart.reduce((s, c) => s + c.price, 0);
    mainButtonAction = () => checkoutCart();
    try { mb.setParams({ text: "💳 " + wt("pay_with_balance_btn", fmt(total)) }); } catch (e) {}
    show = true;
  } else if (!page && activeViewId() === "view-game" && state.selectedPkg) {
    mainButtonAction = () => openPay();
    try { mb.setParams({ text: "🛒 " + wt("buy") }); } catch (e) {}
    show = true;
  }
  document.body.classList.toggle("tg-main-active", show);
  try { show ? mb.show() : mb.hide(); } catch (e) {}
  if (!show) mainButtonAction = null;
}

function initTg() {
  if (!tg) return;
  tg.ready();
  tg.expand();
  tg.disableVerticalSwipes?.();
  try { tg.onEvent?.("themeChanged", () => { if (state.themeMode === "auto") applyTheme("auto", false); }); } catch (e) {}
  try {
    tg.BackButton?.onClick(() => {
      if (topPage()) closePage();
      else goBack();
    });
  } catch (e) {}
  try {
    tg.MainButton?.onClick(() => { if (typeof mainButtonAction === "function") mainButtonAction(); });
  } catch (e) {}
  const savedMode = localStorage.getItem("gs_theme_mode");
  const saved = localStorage.getItem("gs_theme");
  applyTheme(savedMode || saved || "auto", false);
}

function toast(msg, ms = 2800) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove("show"), ms);
}

function addRipple(el, e) {
  if (el.querySelector(".ripple")) return;
  const rect = el.getBoundingClientRect();
  const r = document.createElement("span");
  r.className = "ripple";
  const size = Math.max(rect.width, rect.height);
  r.style.width = r.style.height = size + "px";
  r.style.left = (e.clientX - rect.left - size / 2) + "px";
  r.style.top = (e.clientY - rect.top - size / 2) + "px";
  el.style.position = el.style.position || "relative";
  el.appendChild(r);
  r.addEventListener("animationend", () => r.remove());
}

document.addEventListener("click", (e) => {
  const btn = e.target.closest("button, .game-card, .product-card, .method-chip, .amount-chip, .cat-chip, .nav-item, .service-row, .saved-chip, .pay-copy, .qa-btn, .fav-filter, .icon-btn, .pmethod");
  if (btn) addRipple(btn, e);
}, true);

async function api(path, body) {
  try {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...body, initData: tg?.initData || "" }),
    });
    return await res.json();
  } catch (e) {
    toast(wt("err_network"));
    return { ok: false };
  }
}

/* ---------------- SKELETON ---------------- */
function skeletonGames(n = 6) {
  const grid = document.getElementById("games-grid");
  if (!grid) return;
  grid.innerHTML = Array.from({ length: n }, () =>
    `<div class="sk sk-card" style="height:110px"></div>`
  ).join("");
}
function skeletonList(el) {
  if (!el) return;
  el.innerHTML = Array.from({ length: 4 }, () =>
    `<div class="h-card"><div class="sk sk-line w40"></div><div class="sk sk-line"></div><div class="sk sk-line w60"></div></div>`
  ).join("");
}
function skeletonProducts(el, n = 8) {
  if (!el) return;
  el.innerHTML = Array.from({ length: n }, () =>
    `<div class="sk sk-prod"></div>`
  ).join("");
}

/* ---------------- NAVIGATION ---------------- */
function moveNavGlow(view) {
  const glow = document.getElementById("nav-glow");
  const btn = document.querySelector(`#bottom-nav .nav-item[data-view="${view}"]`);
  if (!glow || !btn) return;
  if (btn.offsetParent === null || getComputedStyle(glow).display === "none") {
    glow.style.opacity = "0";
    return;
  }
  glow.style.opacity = "1";
  glow.style.left = btn.offsetLeft + "px";
  glow.style.width = btn.offsetWidth + "px";
  glow.classList.remove("moving");
  void glow.offsetWidth;
  glow.classList.add("moving");
}

function openView(view, dir) {
  const next = document.getElementById(view);
  const cur = document.querySelector(".view.active");
  const forward = dir !== "back";
  if (cur && cur !== next) {
    const leaving = cur;
    leaving.classList.remove("active", "enter-fwd", "enter-back");
    leaving.classList.add("leaving", forward ? "leave-fwd" : "leave-back");
    leaving.style.top = `-${window.scrollY}px`;
    setTimeout(() => {
      leaving.classList.remove("leaving", "leave-fwd", "leave-back");
      leaving.style.top = "";
    }, 380);
  }
  if (next) {
    next.classList.remove("leaving", "leave-fwd", "leave-back", "enter-fwd", "enter-back");
    next.classList.add("active");
    if (!cur || cur !== next) {
      void next.offsetWidth;
      next.classList.add(forward ? "enter-fwd" : "enter-back");
      setTimeout(() => next.classList.remove("enter-fwd", "enter-back"), 480);
      next.querySelectorAll(".product-card, .game-card, .h-card, .empty-state, .stagger-list > *").forEach((el) => {
        el.style.animation = "none";
        void el.offsetWidth;
        el.style.animation = "";
      });
    }
  }
  document.getElementById("bottom-nav").style.display =
    view === "view-home" || view === "view-history" || view === "view-settings" || view === "view-admin" ? "flex" : "none";
  document.querySelectorAll(".nav-item").forEach((b) =>
    b.classList.toggle("active", b.dataset.view === view)
  );
  moveNavGlow(view);
  syncTgChrome();
  syncMainButton();
  haptic("selection");
  window.scrollTo({ top: 0, behavior: "instant" });
  if (view === "view-home") renderHome();
  if (view === "view-history") loadHistory();
  if (view === "view-settings") renderSettings();
  if (view === "view-topup") renderTopup();
  if (view === "view-admin") loadAdmin();
  if (view === "view-game" && state.currentGame) renderGame();
}

function goBack() {
  const parent = state.backStack.pop() || "view-home";
  openView(parent, "back");
}

/* -------- PAGES + DRAG TO CLOSE -------- */
const pageStack = [];
function topPage() { return pageStack.length ? pageStack[pageStack.length - 1] : null; }
function activeViewId() {
  const v = document.querySelector(".view.active");
  return v ? v.id : "view-home";
}

function openPage(id) {
  if (topPage()) {
    const curEl = document.getElementById(topPage().id);
    if (curEl) curEl.classList.remove("active");
  }
  pageStack.push({ id, prevId: topPage() ? topPage().id : activeViewId() });
  const el = document.getElementById(id);
  if (el) { el.classList.remove("closing"); el.classList.add("active"); el.style.transform = ""; el.style.opacity = ""; }
  haptic("selection");
  enableDragClose(el);
  syncTgChrome();
  syncMainButton();
}

function closePage() {
  const cur = pageStack.pop();
  if (!cur) return;
  const curEl = document.getElementById(cur.id);
  if (curEl) {
    const wasDragged = !!curEl.style.transform;
    curEl.classList.remove("active");
    curEl.style.transform = "";
    curEl.style.opacity = "";
    if (!wasDragged) {
      curEl.classList.add("closing");
      setTimeout(() => curEl.classList.remove("closing"), 260);
    }
  }
  const backEl = document.getElementById(cur.prevId);
  if (!backEl) { openView("view-home"); return; }
  if (backEl.classList.contains("page")) backEl.classList.add("active");
  else openView(cur.prevId);
  syncTgChrome();
  syncMainButton();
}

const _dragBound = new WeakSet();
function enableDragClose(el) {
  if (!el || _dragBound.has(el)) return;
  _dragBound.add(el);
  let startY = 0, curY = 0, dragging = false, startT = 0;
  const header = el.querySelector(".page-header") || el;
  const onDown = (e) => {
    if (e.target.closest("button, input, .pay-copy, .pmethod")) return;
    dragging = true; startY = e.touches ? e.touches[0].clientY : e.clientY;
    curY = startY; startT = Date.now();
    el.classList.add("dragging");
  };
  const onMove = (e) => {
    if (!dragging) return;
    curY = e.touches ? e.touches[0].clientY : e.clientY;
    const dy = Math.max(0, curY - startY);
    el.style.transform = `translateY(${dy}px)`;
    el.style.opacity = String(Math.max(0.4, 1 - dy / 500));
  };
  const onUp = () => {
    if (!dragging) return;
    dragging = false;
    el.classList.remove("dragging");
    const dy = Math.max(0, curY - startY);
    const dt = Date.now() - startT;
    const vel = dy / Math.max(1, dt);
    if (dy > 130 || vel > 0.55) {
      el.classList.add("drag-anim");
      el.style.transform = `translateY(100%)`;
      el.style.opacity = "0";
      setTimeout(() => { el.classList.remove("drag-anim"); closePage(); }, 280);
    } else {
      el.classList.add("drag-anim");
      el.style.transform = "";
      el.style.opacity = "";
      setTimeout(() => el.classList.remove("drag-anim"), 300);
    }
  };
  header.addEventListener("touchstart", onDown, { passive: true });
  header.addEventListener("touchmove", onMove, { passive: true });
  header.addEventListener("touchend", onUp);
  header.addEventListener("mousedown", onDown);
  window.addEventListener("mousemove", onMove);
  window.addEventListener("mouseup", onUp);
}

document.querySelectorAll(".page").forEach(p => enableDragClose(p));

/* ---------------- EMPTY STATE HELPER ---------------- */
function emptyHtml(emoji, title, text, cta = "", ctaOnclick = "") {
  return `<div class="empty-state">
    <span class="empty-emoji">${emoji}</span>
    <div class="empty-title">${esc(title)}</div>
    <div class="empty-text">${esc(text)}</div>
    ${cta ? `<button class="empty-cta" onclick="${ctaOnclick}">${esc(cta)}</button>` : ""}
  </div>`;
}

/* ---------------- HOME ---------------- */
function renderUser() {
  if (!state.user) return;
  const bal = document.getElementById("home-balans");
  const gb = document.getElementById("game-balans");
  const bb = document.getElementById("balance-banner");
  if (bal) bal.textContent = `💰 ${fmt(state.user.balance)} ${wt("sum_suffix")}`;
  if (gb) gb.textContent = `💰 ${fmt(state.user.balance)} ${wt("sum_suffix")}`;
  if (bb) countUp(bb, state.user.balance, " " + wt("sum_suffix"));
}

function setGameFilter(f) {
  state.homeGameFilter = f;
  document.querySelectorAll("#game-filter-bar .gfilter").forEach(b =>
    b.classList.toggle("active", b.dataset.gid === f)
  );
  renderHome();
  haptic("selection");
}

function renderGameFilterBar() {
  const bar = document.getElementById("game-filter-bar");
  if (!bar) return;
  bar.innerHTML = "";
  const mk = (id, emoji, label) => {
    const b = document.createElement("button");
    b.className = "gfilter" + (state.homeGameFilter === id ? " active" : "");
    b.dataset.gid = id;
    b.innerHTML = `${emoji || "🎮"} <span>${esc(label)}</span>`;
    b.onclick = () => setGameFilter(id);
    bar.appendChild(b);
  };
  mk("all", "🎮", wt("cat_all"));
  state.games.forEach(g => mk(g.id, g.emoji, g.name));
}

function setHomeFilter(f) {
  state.homeFilter = f;
  document.getElementById("fav-all")?.classList.toggle("active", f === "all");
  document.getElementById("fav-only")?.classList.toggle("active", f === "fav");
  renderHome();
  haptic("selection");
}

/* ---------- O'yin brend ranglari + logolar ---------- */
const GAME_BRAND = {
  freefire: { b1: "#ff9a3c", b2: "#ff2d00", glow: "rgba(255,106,0,.5)", plate: "light", wide: true },
  pubg:     { b1: "#3a3f4a", b2: "#0b0d12", glow: "rgba(244,185,66,.45)", plate: "dark" },
  ml:       { b1: "#29b6f6", b2: "#0d47a1", glow: "rgba(41,182,246,.5)", plate: "light", wide: true },
  roblox:   { b1: "#ff5a5f", b2: "#b3141b", glow: "rgba(255,90,95,.5)", plate: "dark" },
  standoff: { b1: "#7c5cfc", b2: "#31169e", glow: "rgba(124,92,252,.5)", plate: "dark", wide: true },
  stars:    { b1: "#ffca28", b2: "#ff6d00", glow: "rgba(255,180,40,.5)", emoji: "⭐️" },
  premium:  { b1: "#a78bfa", b2: "#0e7490", glow: "rgba(167,139,250,.5)", emoji: "💎" },
};
const GAME_LOGO_EXT = { freefire: "svg", pubg: "svg", ml: "png", roblox: "svg", standoff: "svg" };

function brandStyle(g) {
  const b = (g && GAME_BRAND[g.id]) || {};
  return `--b1:${b.b1 || "#7c5cfc"};--b2:${b.b2 || "#4cc9f0"};--glow:${b.glow || "rgba(124,92,252,.4)"}`;
}
function logoInner(g, hero) {
  const b = (g && GAME_BRAND[g.id]) || {};
  const ext = g && GAME_LOGO_EXT[g.id];
  if (ext) return `<img src="/static/img/games/${g.id}.${ext}?v=2" alt="${esc(g ? g.name : "")}" loading="lazy">`;
  return `<span class="${hero ? "gh-emoji" : "g-emoji"}">${b.emoji || (g && g.emoji) || "🎮"}</span>`;
}

function renderHome() {
  const grid = document.getElementById("games-grid");
  const favEmpty = document.getElementById("fav-empty");
  if (!grid) return;
  grid.innerHTML = "";
  grid.classList.add("stagger-list");

  let list = state.games;
  if (state.homeFilter === "fav") {
    const favIds = new Set(state.favorites.map(f => f.game_id));
    list = state.games.filter(g => favIds.has(g.id));
    if (!list.length) {
      grid.innerHTML = "";
      if (favEmpty) favEmpty.style.display = "block";
      return;
    }
  } else {
    // show fav star hint on cards
  }
  if (state.homeGameFilter && state.homeGameFilter !== "all") {
    list = list.filter(g => g.id === state.homeGameFilter);
  }
  if (favEmpty) favEmpty.style.display = "none";

  if (!list.length) {
    grid.innerHTML = emptyHtml("🎮", wt("no_games"), wt("catalog_empty"));
    return;
  }

  const favIds = new Set(state.favorites.map(f => f.game_id));
  list.forEach((g) => {
    const isFav = favIds.has(g.id);
    const card = document.createElement("div");
    card.className = "game-card";
    card.setAttribute("style", brandStyle(g));
    card.innerHTML = `
      <div class="g-strip">${logoInner(g)}<span class="g-shine"></span></div>
      <div class="g-body">
        <div class="game-name">${esc(g.name)}</div>
        <div class="game-desc">${esc(g.desc || "")}</div>
      </div>
      <div class="p-fav ${isFav ? "on" : ""}" data-gid="${g.id}" onclick="event.stopPropagation();quickFav('${g.id}',this)">${isFav ? "⭐️" : "☆"}</div>`;
    card.onclick = () => openGame(g.id);
    grid.appendChild(card);
  });
}

async function quickFav(gameId, el) {
  const res = await api("/api/favorites", { game_id: gameId, toggle: true });
  if (res.ok) {
    state.favorites = res.favorites || [];
    const on = res.active;
    if (el) { el.classList.toggle("on", on); el.textContent = on ? "⭐️" : "☆"; }
    haptic("success");
    if (state.homeFilter === "fav") renderHome();
    toast(on ? wt("fav_added") : wt("fav_removed"));
  }
}

async function toggleGameFav() {
  if (!state.currentGame) return;
  const res = await api("/api/favorites", { game_id: state.currentGame.id, toggle: true });
  if (res.ok) {
    state.favorites = res.favorites || [];
    state.gameIsFav = !!res.active;
    const btn = document.getElementById("game-fav-btn");
    if (btn) btn.textContent = state.gameIsFav ? "⭐️" : "☆";
    haptic("success");
    toast(state.gameIsFav ? wt("fav_added") : wt("fav_removed"));
  }
}

async function openGame(gameId) {
  skeletonProducts(document.getElementById("products-grid"), 8);
  const res = await api("/api/game", { game_id: gameId });
  if (!res.ok) return toast(wt("game_not_found"));
  state.currentGame = res.game;
  state.canVerify = !!res.can_verify;
  state.savedIds = res.saved_ids || [];
  state.selectedPkg = null;
  state.playerId = "";
  state.verifiedName = null;
  state.activeCat = "all";
  state.gameIsFav = state.favorites.some(f => f.game_id === gameId);
  state.backStack = ["view-home"];
  resetPkgFilters(true);
  openView("view-game");
  loadLastOrder(gameId);
}

function renderGame() {
  const g = state.currentGame;
  if (!g) return;
  const b = GAME_BRAND[g.id] || {};
  const view = document.getElementById("view-game");
  view.style.setProperty("--brand1", b.b1 || "#7c5cfc");
  view.style.setProperty("--brand2", b.b2 || "#4cc9f0");
  view.style.setProperty("--brand-glow", b.glow || "rgba(124,92,252,.4)");
  const hero = document.getElementById("game-hero");
  if (hero) {
    hero.setAttribute("style", brandStyle(g));
    hero.classList.remove("hero-in");
    void hero.offsetWidth;
    hero.classList.add("hero-in");
  }
  const ghName = document.getElementById("gh-name");
  if (ghName) ghName.textContent = g.name;
  const ghDesc = document.getElementById("gh-desc");
  if (ghDesc) ghDesc.textContent = g.desc || "";
  const ghLogo = document.getElementById("gh-logo");
  if (ghLogo) {
    const ext = GAME_LOGO_EXT[g.id];
    ghLogo.className = "gh-logo" + (ext ? (b.plate === "light" ? " light" : "") + (b.wide ? " wide" : "") : "");
    ghLogo.innerHTML = logoInner(g, true);
  }
  document.getElementById("game-title").textContent = g.name;
  const favBtn = document.getElementById("game-fav-btn");
  if (favBtn) favBtn.textContent = state.gameIsFav ? "⭐️" : "☆";
  document.getElementById("verify-btn").style.display = state.canVerify ? "" : "none";
  const ph = g.game_id_placeholder || wt("enter_id");
  const inp = document.getElementById("player-id");
  inp.placeholder = ph;
  inp.onkeydown = (e) => {
    if (e.key === "Enter" && state.canVerify) verifyId();
    else if (e.key === "Enter") { state.playerId = inp.value.trim(); toast(wt("id_ok")); }
  };
  const catWrap = document.getElementById("cat-tabs");
  catWrap.innerHTML = "";
  if (g.categories) {
    catWrap.style.display = "flex";
    Object.entries(g.categories).forEach(([key, name]) => {
      const chip = document.createElement("button");
      chip.className = "cat-chip" + (state.activeCat === key ? " active" : "");
      chip.textContent = name;
      chip.onclick = () => { state.activeCat = key; renderGame(); haptic("selection"); };
      catWrap.appendChild(chip);
    });
  } else {
    catWrap.style.display = "none";
    state.activeCat = "all";
  }
  const savedWrap = document.getElementById("saved-ids");
  savedWrap.innerHTML = "";
  if (state.savedIds.length) {
    savedWrap.innerHTML = `<span style="font-size:11px;color:var(--muted);font-weight:700">${wt("saved_ids_title")}</span>`;
  }
  state.savedIds.forEach((id) => {
    const chip = document.createElement("div");
    chip.className = "saved-chip";
    chip.textContent = id;
    chip.onclick = () => {
      document.getElementById("player-id").value = id;
      state.playerId = id;
      verifyId();
    };
    savedWrap.appendChild(chip);
  });

  const grid = document.getElementById("products-grid");
  const empty = document.getElementById("products-empty");
  const filterEmpty = document.getElementById("products-filter-empty");
  grid.innerHTML = "";
  grid.classList.add("stagger-list");
  let packages = state.activeCat !== "all" ? g.packages.filter((p) => p.category === state.activeCat) : g.packages.slice();
  const q = (state.pkgSearch || "").trim().toLowerCase();
  if (q) packages = packages.filter(p => (p.name || "").toLowerCase().includes(q));
  const minP = Number(String(state.pkgMin).replace(/[^\d]/g, "")) || 0;
  const maxP = Number(String(state.pkgMax).replace(/[^\d]/g, "")) || 0;
  if (minP) packages = packages.filter(p => p.price >= minP);
  if (maxP) packages = packages.filter(p => p.price <= maxP);
  if (state.pkgSort === "cheap") packages.sort((a, b) => a.price - b.price);
  else if (state.pkgSort === "expensive") packages.sort((a, b) => b.price - a.price);
  const filterActive = !!(q || minP || maxP || state.pkgSort !== "default");
  if (!packages.length) {
    grid.innerHTML = "";
    if (empty) empty.style.display = filterActive ? "none" : "block";
    if (filterEmpty) filterEmpty.style.display = filterActive ? "block" : "none";
  } else {
    if (empty) empty.style.display = "none";
    if (filterEmpty) filterEmpty.style.display = "none";
    packages.forEach((p) => {
      const el = document.createElement("div");
      el.className = "product-card" + (g.grid_mode ? " grid" : "");
      const badge = p.badge ? `<div class="p-badge">${esc(p.badge)}</div>` : (p.hit ? `<div class="p-badge hot">HIT</div>` : "");
      const inCart = state.cart.some(c => c.gameId === g.id && c.pkgId === p.id);
      const amt = p.amount != null && String(p.amount).trim() !== "" ? String(p.amount).trim() : "";
      const hasAmt = !!amt && p.name.includes(amt);
      const rest = hasAmt ? p.name.replace(amt, "").replace(/\s+/g, " ").trim() : "";
      const oyKey = amt ? (amt.endsWith(" oy") ? amt : `${amt} oy`) : "";
      let big, sub;
      if (oyKey && p.name.includes(oyKey)) {
        big = oyKey;
        sub = p.name.replace(oyKey, "").replace(/\s+/g, " ").trim();
      } else if (p.unit && amt) {
        big = `${amt} ${p.unit}`;
        sub = p.name;
      } else if (hasAmt && rest) {
        big = amt;
        sub = rest;
      } else {
        big = p.name.split(" ")[0];
        sub = p.name.length > 12 ? shortName(p.name) : "";
      }
      el.innerHTML = `
        <div class="p-check">✓</div>
        <div class="p-amount">${esc(big)}</div>
        <div class="p-price">${fmt(p.price)} ${wt("sum_suffix")}</div>
        ${badge}
        ${sub ? `<div style="font-size:10px;color:var(--muted);margin-top:2px">${esc(sub)}</div>` : ""}
        ${inCart ? `<div style="font-size:10px;color:var(--ok);margin-top:4px;font-weight:800">${wt("in_cart")}</div>` : ""}`;
      el.onclick = () => selectPkg(p, el);
      grid.appendChild(el);
    });
  }
  document.getElementById("verify-result").style.display = "none";
  document.getElementById("buy-bar").style.display = "none";
}

function shortName(name) {
  return name.length > 12 ? name.slice(0, 11) + "…" : name;
}

function selectPkg(pkg, el) {
  document.querySelectorAll(".product-card").forEach((c) => c.classList.remove("selected"));
  el.classList.add("selected");
  state.selectedPkg = pkg;
  document.getElementById("buy-name").textContent = `${state.currentGame.name} — ${pkg.name}`;
  document.getElementById("buy-price").textContent = `${fmt(pkg.price)} ${wt("sum_suffix")}`;
  document.getElementById("buy-bar").style.display = "flex";
  syncMainButton();
  haptic("selection");
}

/* ---------------- PRODUCT SEARCH / FILTER ---------------- */
function onPkgSearch() {
  const inp = document.getElementById("pkg-search");
  const clear = document.getElementById("pkg-search-clear");
  state.pkgSearch = inp ? inp.value : "";
  if (clear) clear.style.display = state.pkgSearch ? "flex" : "none";
  renderGame();
}

function clearPkgSearch() {
  const inp = document.getElementById("pkg-search");
  if (inp) inp.value = "";
  state.pkgSearch = "";
  const clear = document.getElementById("pkg-search-clear");
  if (clear) clear.style.display = "none";
  renderGame();
  haptic("light");
}

function setPkgSort(sort) {
  state.pkgSort = sort;
  document.querySelectorAll("#pkg-sort-tabs .seg-sort").forEach((b) =>
    b.classList.toggle("active", b.dataset.sort === sort)
  );
  renderGame();
  haptic("selection");
}

function onPkgPrice() {
  const minEl = document.getElementById("pkg-min");
  const maxEl = document.getElementById("pkg-max");
  state.pkgMin = minEl ? minEl.value.trim() : "";
  state.pkgMax = maxEl ? maxEl.value.trim() : "";
  renderGame();
}

function resetPkgFilters(silent) {
  state.pkgSearch = "";
  state.pkgSort = "default";
  state.pkgMin = "";
  state.pkgMax = "";
  const inp = document.getElementById("pkg-search");
  if (inp) inp.value = "";
  const clear = document.getElementById("pkg-search-clear");
  if (clear) clear.style.display = "none";
  const minEl = document.getElementById("pkg-min");
  const maxEl = document.getElementById("pkg-max");
  if (minEl) minEl.value = "";
  if (maxEl) maxEl.value = "";
  document.querySelectorAll("#pkg-sort-tabs .seg-sort").forEach((b) =>
    b.classList.toggle("active", b.dataset.sort === "default")
  );
  if (!silent && state.currentGame) renderGame();
}

/* ---------------- VERIFY ---------------- */
async function verifyId() {
  const inp = document.getElementById("player-id");
  const val = inp.value.trim();
  if (!val) { toast(wt("id_enter")); haptic("error"); return false; }
  state.playerId = val;
  const btn = document.getElementById("verify-btn");
  btn.disabled = true;
  btn.textContent = wt("verifying");
  try {
    const res = await api("/api/verify", { game_id: state.currentGame.id, player_id: val });
    const box = document.getElementById("verify-result");
    if (res.ok) {
      state.verifiedName = res.name;
      box.classList.remove("error");
      box.style.display = "block";
      box.innerHTML = wt("id_found_ok", `<b>${esc(res.name)}</b>`);
      haptic("success");
      if (!state.savedIds.includes(val)) {
        state.savedIds.unshift(val);
        state.savedIds = state.savedIds.slice(0, 5);
        renderGame();
        document.getElementById("player-id").value = val;
      }
      return true;
    }
    state.verifiedName = null;
    box.classList.add("error");
    box.style.display = "block";
    box.textContent = (res.message || wt("wrong_verify")) + " " + wt("can_continue");
    haptic("error");
    return false;
  } finally {
    btn.disabled = false;
    btn.textContent = "Tekshirish";
  }
}

/* ---------------- PAYMENT ---------------- */
async function openPay() {
  if (!state.selectedPkg) return toast(wt("select_product"));
  if (!state.playerId) {
    const inp = document.getElementById("player-id");
    const v = inp.value.trim();
    if (!v) return toast(wt("enter_id"));
    state.playerId = v;
  }
  if (state.canVerify) {
    const inpVal = document.getElementById("player-id").value.trim();
    const needVerify = !state.verifiedName || state.playerId !== inpVal;
    if (needVerify) {
      const ok = await verifyId();
      if (!ok) return;
    }
  }
  document.getElementById("pay-amount").textContent = fmt(state.selectedPkg.price);
  document.getElementById("pm-balance").textContent = `${fmt(state.user.balance)} ${wt("sum_suffix")}`;
  openPage("pay-sheet");
}

function closePay() { closePage(); }

async function chooseMethod(method) {
  if (!state.selectedPkg) return;
  if (state._sending) return; // double-click himoya: 2-chi bosish e'tiborsiz
  const _gId = state.currentGame ? state.currentGame.id : 0;
  const _pId = state.selectedPkg.id;
  state._sending = true;
  haptic("success");
  try {
    closePay();
    const res = await api("/api/order", {
      game_id: state.currentGame.id,
      package_id: state.selectedPkg.id,
      player_id: state.playerId,
      method,
    });
  if (!res.ok) {
    if (res.error === "maintenance") return toast(wt("maintenance_msg"));
    if (res.error === "bad_player_id") return toast(`⚠️ ${res.message || wt("err_generic")}`);
    return toast(wt("err_generic"));
  }

  if (res.need_balance) {
    toast(wt("no_balance"));
    openView("view-topup");
    return;
  }
  if (res.need_payment) {
    dropFromCart(_gId, _pId);
    resetOrder();
    showManual({ title: "⭐️ Telegram Stars", body: wt("stars_req2") });
    return;
  }
  if (res.need_manual) {
    dropFromCart(_gId, _pId);
    resetOrder();
    openPayTimer(res);
    return;
  }
  if (res.ok) {
    dropFromCart(_gId, _pId);
    if (res.duplicate) {
      toast("ℹ️ " + res.message);
      if (typeof res.balance === "number") {
        state.user.balance = res.balance;
        renderUser();
      }
      closePay();
      return;
    }
    toast("✅ " + res.message);
    if (res.player_name) {
      toast(`👤 ${wt("player_name")}: ${esc(res.player_name)}`);
    }
    countUp(document.getElementById("balance-banner"), (state.user.balance || 0) - state.selectedPkg.price, " " + wt("sum_suffix"));
    state.user.balance = (state.user.balance || 0) - state.selectedPkg.price;
    renderUser();
    pulseBalance();
    successBurst();
    resetOrder();
    haptic("success");
  }
  } finally {
    state._sending = false;
  }
}

function showManual({ title, body }) {
  document.getElementById("manual-title").textContent = title;
  document.getElementById("manual-content").innerHTML = `
    <div class="manual-inst">${body}</div>
    <button class="big-btn" onclick="closePage()" style="margin-top:16px">${wt("close_btn")}</button>`;
  openPage("manual-sheet");
}

function cardsFrom(res) {
  if (Array.isArray(res.cards_list) && res.cards_list.length) return res.cards_list;
  if (Array.isArray(res.cards) && res.cards.length && res.cards[0] && res.cards[0].number !== undefined) return res.cards;
  const map = res.cards && typeof res.cards === "object" ? res.cards : {};
  const labels = { uzcard: "Uzcard", humo: "Humo", tbc: "Tbc", uzum: "Uzum" };
  const out = [];
  for (const [key, label] of Object.entries(labels)) {
    const num = map[key] || res["card_" + key] || "";
    if (num) out.push({ key, label, number: num, holder: res.card_name || "" });
  }
  if (!out.length && res.card_number) out.push({ key: "uzcard", label: wt("card_word"), number: res.card_number, holder: res.card_name || "" });
  return out;
}

function cardsHtmlEsc(res) {
  const cards = cardsFrom(res);
  if (!cards.length) return "";
  return cards.map((c) => `<br>💳 <b>${esc(c.label)}:</b> <code>${esc(c.number)}</code>${c.holder ? ` (${esc(c.holder)})` : ""}`).join("");
}

function showManualResult(res) {
  const methodName = { paynet: "PAYNET", uzqr: wt("pay_uzqr"), card: wt("pay_by_card") }[res.method] || res.method;
  const cards = cardsHtmlEsc(res);
  const contact = [];
  if (res.support_phone || res.card_phone) contact.push(`<br>📞 <code>${esc(res.support_phone || res.card_phone)}</code>`);
  if (res.support_email) contact.push(`<br>📧 <code>${esc(res.support_email)}</code>`);
  if (res.admin_username) contact.push(`<br>👤 ${wt("contact_ask")}: <b>@${esc(res.admin_username)}</b>`);
  showManual({
    title: res.method === "card" ? "💳 " + wt("pay_by_card") : "📲 " + methodName,
    body: `${wt("pay_transfer", fmt(res.amount) + " " + wt("sum_suffix"))}${cards}${contact.join("")}<br><br>${wt("pay_no")}: <b>#${res.payment_id}</b>${res.order_id ? `<br>${wt("order_no")}: <b>#${res.order_id}</b>` : ""}<br><br>${wt("pay_after_tx")}`,
  });
}

/* -------- PAY TIMER -------- */
let payTimer = null;
let payTimerEnd = 0;

function openPayTimer(res) {
  if (payTimer) { clearInterval(payTimer); payTimer = null; }
  payTimerEnd = Date.now() + (res.pay_window_seconds || state.payWindowSecs) * 1000;
  const methodName = { paynet: "PAYNET", uzqr: wt("pay_uzqr"), card: wt("pay_by_card") }[res.method] || res.method;

  let details = "";
  if (res.method === "card") {
    const cards = cardsFrom(res);
    const labels = { uzcard: "Uzcard", humo: "Humo", tbc: "Tbc", uzum: "Uzum" };
    if (cards.length) {
      for (const c of cards) {
        const num = c.number || "";
        const label = labels[c.key] || c.label || c.key;
        details += `<div class="pay-row">💳 <b>${esc(label)}</b>${c.holder ? ` (${esc(c.holder)})` : ""}</div><div class="pay-copy" onclick="copyText(this.dataset.txt)" data-txt="${esc(num)}">${esc(num)} 📋</div>`;
      }
    } else if (res.card_number) {
      details += `<div class="pay-row">💳 <b>${wt("card_word")}</b></div><div class="pay-copy" onclick="copyText(this.dataset.txt)" data-txt="${esc(res.card_number)}">${esc(res.card_number)} 📋</div>`;
    }
    if (res.card_name) details += `<div class="pay-row">👤 <b>${wt("owner_word")}</b></div><div class="pay-copy">${esc(res.card_name)}</div>`;
  } else {
    details += `<div class="pay-row">📲 <b>${esc(methodName)}</b></div>`;
    const phone = res.card_phone || res.support_phone || "";
    if (phone) details += `<div class="pay-row">📞 <b>${wt("number_word")}</b></div><div class="pay-copy" onclick="copyText(this.dataset.txt)" data-txt="${esc(phone)}">${esc(phone)} 📋</div>`;
  }
  const phone2 = res.support_phone || res.card_phone || "";
  if (phone2 && res.method === "card") details += `<div class="pay-row">📞 <b>${wt("phone_word")}</b></div><div class="pay-copy" onclick="copyText(this.dataset.txt)" data-txt="${esc(phone2)}">${esc(phone2)} 📋</div>`;
  if (res.support_email) details += `<div class="pay-row">📧 <b>${wt("email_word")}</b></div><div class="pay-copy" onclick="copyText(this.dataset.txt)" data-txt="${esc(res.support_email)}">${esc(res.support_email)} 📋</div>`;
  const support = res.support || "";
  if (support) details += `<div class="pay-row">💬 <b>Support</b></div><div class="pay-copy" onclick="copyText(this.dataset.txt)" data-txt="${esc(support)}">${esc(support)} 📋</div>`;
  if (res.admin_username) details += `<div class="pay-row">🧑‍💻 <b>${wt("contact_ask")}</b></div><div class="pay-copy" onclick="copyText(this.dataset.txt)" data-txt="@${esc(res.admin_username)}">@${esc(res.admin_username)} 📋</div>`;

  const el = document.getElementById("paytimer-body");
  el.innerHTML = `
    <div class="pay-amount">${fmt(res.amount)} ${wt("sum_suffix")}</div>
    <div class="manual-inst" style="text-align:center">
      ${details}
      <div style="margin:12px 0 2px">${wt("pay_no")}: <b>#${res.payment_id}</b>${res.order_id ? ` · ${wt("order_no")}: <b>#${res.order_id}</b>` : ""}</div>
    </div>
    <div class="pay-count" id="pay-count">⏱ ${fmtSec(res.pay_window_seconds || state.payWindowSecs)}</div>
    <div class="pay-hint">${wt("pay_hint")}</div>
    <button class="big-btn" onclick="openReceiptFromTimer(${res.payment_id || 0},${res.order_id || 0},${res.amount || 0},'${esc(methodName)}')">🧾 ${wt("view_receipt")}</button>
    <button class="big-btn" id="pay-send-btn" onclick="openBotChat()">📤 ${wt("send_receipt_bot")}</button>
    <button class="big-btn" id="pay-admin-btn" style="display:none;background:var(--accent2)" onclick="openAdminChat()">🧑‍💻 ${wt("ask_admin")}</button>
    <button class="ghost-btn" id="pay-close-btn" onclick="closePayTimer()">${wt("exit")}</button>`;
  openPage("paytimer-sheet");
  tick();
  payTimer = setInterval(tick, 1000);
}

function openReceiptFromTimer(paymentId, orderId, amount, method) {
  showReceipt({ id: orderId || paymentId, payment_id: paymentId, amount, method, status: "to'lov_kutilmoqda", created_at: new Date().toLocaleString("ru-RU"), package_name: "", platform_name: "DONATE FM", player_id: state.playerId || "" });
}

function fmtSec(sec) {
  sec = Math.max(0, Number(sec) || 0);
  const m = String(Math.floor(sec / 60)).padStart(2, "0");
  const s = String(sec % 60).padStart(2, "0");
  return `${m}:${s}`;
}

function tick() {
  const left = Math.max(0, Math.floor((payTimerEnd - Date.now()) / 1000));
  const c = document.getElementById("pay-count");
  if (!c) return;
  if (left <= 0) {
    clearInterval(payTimer);
    payTimer = null;
    c.textContent = wt("pay_timer_expired");
    c.classList.add("expired");
    document.getElementById("pay-admin-btn").style.display = "block";
  } else {
    c.textContent = `⏱ ${fmtSec(left)}`;
  }
}

function copyText(txt) {
  try { navigator.clipboard.writeText(txt); toast(wt("copied")); }
  catch (e) { toast(txt); }
  haptic("success");
}

function openBotChat() {
  if (tg && state.botUsername) tg.openTelegramLink(`https://t.me/${state.botUsername}`);
  else if (state.inviteLink) {
    const u = new URL(state.inviteLink); u.search = ""; window.open(u.href, "_blank");
  }
  toast(wt("send_receipt"));
}

function openAdminChat() {
  const un = (state.adminUsername || state.supportUsername || "").replace(/^@/, "");
  if (un) {
    if (tg) tg.openTelegramLink(`https://t.me/${un}`);
    else window.open(`https://t.me/${un}`, "_blank");
  } else {
    toast(wt("admin_not_found"));
    if (tg && state.botUsername) tg.openTelegramLink(`https://t.me/${state.botUsername}`);
  }
  closePayTimer();
}

function closePayTimer() {
  if (payTimer) { clearInterval(payTimer); payTimer = null; }
  closePage();
  toast(wt("wait_admin"));
}

function resetOrder() {
  state.selectedPkg = null;
  document.getElementById("buy-bar").style.display = "none";
  document.querySelectorAll(".product-card").forEach((c) => c.classList.remove("selected"));
  syncMainButton();
}

function closeManual() {
  closePage();
  toast(wt("wait_admin"));
}

/* ---------------- CART ---------------- */
function saveCartCloud() {
  const data = JSON.stringify(state.cart || []);
  try {
    if (tg && tg.CloudStorage) {
      tg.CloudStorage.setItem("cart_v1", data, () => {});
    } else {
      localStorage.setItem("gs_cart", data);
    }
  } catch (e) {}
}

function loadCartCloud(cb) {
  const done = (val) => {
    let arr = [];
    try { arr = JSON.parse(val || "[]"); } catch (e) {}
    cb(Array.isArray(arr) ? arr : []);
  };
  try {
    if (tg && tg.CloudStorage) {
      tg.CloudStorage.getItem("cart_v1", (err, val) => done(err ? "[]" : val));
    } else {
      done(localStorage.getItem("gs_cart"));
    }
  } catch (e) { cb([]); }
}

function addToCart() {
  if (!state.selectedPkg || !state.currentGame) return toast(wt("select_product"));
  const srcEl = document.querySelector(".product-card.selected");
  const item = {
    gameId: state.currentGame.id,
    gameName: state.currentGame.name,
    emoji: state.currentGame.emoji || "🎮",
    pkgId: state.selectedPkg.id,
    pkgName: state.selectedPkg.name,
    price: state.selectedPkg.price,
    amount: state.selectedPkg.amount,
  };
  const idx = state.cart.findIndex(c => c.gameId === item.gameId && c.pkgId === item.pkgId);
  if (idx >= 0) state.cart.splice(idx, 1);
  else state.cart.push(item);
  updateCartBadge();
  saveCartCloud();
  if (idx < 0) flyToCart(srcEl, document.getElementById("bb-cart-btn"));
  resetOrder();
  renderGame();
  haptic("success");
  toast(idx >= 0 ? wt("cart_removed") : wt("cart_added"));
}

function updateCartBadge() {
  const n = state.cart.length;
  ["cart-badge", "bb-cart-badge"].forEach((id) => {
    const b = document.getElementById(id);
    if (!b) return;
    if (n) {
      b.style.display = "flex";
      b.textContent = n > 99 ? "99+" : String(n);
      b.classList.remove("pop");
      void b.offsetWidth;
      b.classList.add("pop");
    } else {
      b.style.display = "none";
    }
  });
}

function flyToCart(srcEl, targetEl) {
  const src = srcEl;
  const target = targetEl || document.getElementById("btn-cart");
  if (!src || !target || !target.getClientRects().length || !src.getClientRects().length) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const r = src.getBoundingClientRect();
  const t = target.getBoundingClientRect();
  const fly = document.createElement("div");
  fly.className = "fly-emoji";
  fly.textContent = "🛒";
  fly.style.left = r.left + r.width / 2 - 16 + "px";
  fly.style.top = r.top + r.height / 2 - 16 + "px";
  document.body.appendChild(fly);
  const dx = (t.left + t.width / 2) - (r.left + r.width / 2);
  const dy = (t.top + t.height / 2) - (r.top + r.height / 2);
  const anim = fly.animate([
    { transform: "translate(0,0) scale(.4) rotate(0deg)", opacity: 0 },
    { transform: `translate(${dx * 0.22}px, ${dy * 0.22 - 54}px) scale(1.3) rotate(-16deg)`, opacity: 1, offset: 0.35 },
    { transform: `translate(${dx * 0.7}px, ${dy * 0.7}px) scale(1.05) rotate(12deg)`, opacity: 1, offset: 0.75 },
    { transform: `translate(${dx}px, ${dy}px) scale(0.25) rotate(0deg)`, opacity: 0.2 },
  ], { duration: 780, easing: "cubic-bezier(.3,0,.35,1)" });
  anim.onfinish = () => fly.remove();
}

function pulseBalance() {
  const bb = document.getElementById("balance-banner");
  if (!bb) return;
  bb.classList.remove("pulse");
  void bb.offsetWidth;
  bb.classList.add("pulse");
}

/* ---------------- SUCCESS FX ---------------- */
const REDUCED_MOTION = (() => {
  try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; }
  catch (e) { return false; }
})();

function successBurst() {
  if (REDUCED_MOTION) return;
  lottieSuccess();
  const el = document.createElement("div");
  el.className = "success-burst";
  el.innerHTML =
    '<span class="sb-ring"></span><span class="sb-ring d2"></span>' +
    '<svg class="sb-check" viewBox="0 0 52 52"><path d="M14 27 l8 8 l16 -18"/></svg>';
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 1600);
}

function confettiBurst(n = 26) {
  if (REDUCED_MOTION) return;
  const colors = ["#facc15", "#f43f5e", "#4cc9f0", "#7c5cfc", "#3ddc84", "#fb923c"];
  for (let i = 0; i < n; i++) {
    const p = document.createElement("div");
    p.className = "confetti";
    p.style.left = 18 + Math.random() * 64 + "%";
    p.style.background = colors[i % colors.length];
    p.style.setProperty("--cx", (Math.random() - 0.5) * 170 + "px");
    p.style.animationDuration = 1 + Math.random() * 0.9 + "s";
    p.style.animationDelay = Math.random() * 0.3 + "s";
    document.body.appendChild(p);
    setTimeout(() => p.remove(), 2500);
  }
}

/* ---------------- DAILY BONUS ---------------- */
function fmtHMS(s) {
  s = Math.max(0, Math.floor(s));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const x = s % 60;
  const pad = (v) => String(v).padStart(2, "0");
  return pad(h) + ":" + pad(m) + ":" + pad(x);
}

function renderBonus() {
  const card = document.getElementById("bonus-card");
  if (!card) return;
  const db = state.dailyBonus || { last: 0, amount: 5000 };
  const now = Math.floor(Date.now() / 1000);
  const last = db.last || 0;
  const ready = now - last >= 86400;
  card.classList.toggle("ready", ready);
  card.classList.toggle("claimed", !ready);
  const sub = document.getElementById("bonus-sub");
  const cta = document.getElementById("bonus-cta");
  if (ready) {
    if (sub) sub.textContent = wt("bonus_ready");
    if (cta) cta.textContent = wt("bonus_claim");
  } else {
    if (sub) sub.textContent = wt("bonus_next", fmtHMS(last + 86400 - now));
    if (cta) cta.textContent = wt("bonus_claimed");
  }
}

async function claimDailyBonus() {
  const card = document.getElementById("bonus-card");
  if (!card || card.dataset.busy) return;
  const now = Math.floor(Date.now() / 1000);
  const db = state.dailyBonus || { last: 0, amount: 5000 };
  const last = db.last || 0;
  if (now - last < 86400) {
    toast(wt("bonus_next", fmtHMS(last + 86400 - now)));
    tg?.HapticFeedback?.notificationOccurred?.("error");
    return;
  }
  card.dataset.busy = "1";
  try {
    const res = await api("/api/daily_bonus", {});
    if (res.ok) {
      state.dailyBonus = { last: (res.next_available || now + 86400) - 86400, amount: res.amount };
      state.user.balance = res.balance;
      countUp(document.getElementById("balance-banner"), res.balance, " " + wt("sum_suffix"));
      renderUser();
      successBurst();
      confettiBurst(32);
      haptic("success");
      toast(wt("bonus_got", res.amount));
      renderBonus();
    } else if (res.next_available) {
      state.dailyBonus = { ...(state.dailyBonus || {}), last: res.next_available - 86400 };
      renderBonus();
      toast(wt("bonus_next", fmtHMS(res.next_available - now)));
    }
  } finally {
    delete card.dataset.busy;
  }
}

setInterval(() => {
  const card = document.getElementById("bonus-card");
  if (card && !card.classList.contains("ready")) renderBonus();
}, 1000);

/* ---------------- HERO PARALLAX ---------------- */
let _plxTick = false;
window.addEventListener("scroll", () => {
  if (_plxTick) return;
  _plxTick = true;
  requestAnimationFrame(() => {
    _plxTick = false;
    if (REDUCED_MOTION) return;
    const view = document.getElementById("view-game");
    if (!view || !view.classList.contains("active")) return;
    const hero = document.getElementById("game-hero");
    if (!hero) return;
    const y = Math.min(window.scrollY, 420);
    const o1 = hero.querySelector(".gh-orb-1");
    const o2 = hero.querySelector(".gh-orb-2");
    const logo = hero.querySelector(".gh-logo");
    if (o1) o1.style.translate = "0 " + y * 0.3 + "px";
    if (o2) o2.style.translate = "0 " + y * 0.46 + "px";
    if (logo) logo.style.translate = "0 " + y * 0.12 + "px";
  });
}, { passive: true });

function dropFromCart(gameId, pkgId) {
  const i = state.cart.findIndex((c) => c.gameId === gameId && c.pkgId === pkgId);
  if (i < 0) return;
  state.cart.splice(i, 1);
  updateCartBadge();
  const wrap = document.getElementById("cart-list");
  if (wrap) renderCart();
}

function openCart() {
  openPage("cart-sheet");
  renderCart();
}

function renderCart() {
  const wrap = document.getElementById("cart-list");
  if (!wrap) return;
  if (!state.cart.length) {
    wrap.innerHTML = emptyHtml("🛒", wt("cart_empty"), wt("cart_empty_text"), "🎮 " + wt("view_games"), "closePage();openView('view-home')");
    syncMainButton();
    return;
  }
  const total = state.cart.reduce((s, c) => s + c.price, 0);
  wrap.innerHTML = state.cart.map((c, i) => `
    <div class="cart-item" style="animation-delay:${i * 0.05}s">
      <div class="ci-ico">${c.emoji}</div>
      <div class="ci-info">
        <div class="ci-name">${esc(c.gameName)} — ${esc(c.pkgName)}</div>
        <div class="ci-price">${fmt(c.price)} ${wt("sum_suffix")}</div>
      </div>
      <button class="ci-remove" onclick="removeCartItem(${i})">✕</button>
    </div>`).join("") + `
    <div class="cart-total">
      <span class="ct-label">Jami (${state.cart.length} ta)</span>
      <span class="ct-val">${fmt(total)} ${wt("sum_suffix")}</span>
    </div>
    <button class="big-btn" onclick="checkoutCart()">${wt("pay_with_balance_btn", fmt(total))}</button>
    <button class="ghost-btn" onclick="clearCart()">${wt("clear_cart2")}</button>`;
  syncMainButton();
}

function removeCartItem(i) {
  state.cart.splice(i, 1);
  updateCartBadge();
  saveCartCloud();
  renderCart();
  haptic("selection");
}

function clearCart() {
  state.cart = [];
  updateCartBadge();
  saveCartCloud();
  renderCart();
  toast(wt("cart_cleared"));
}

async function checkoutCart() {
  if (!state.cart.length) return;
  if (!state.playerId) {
    const inp = document.getElementById("player-id");
    state.playerId = (inp && inp.value.trim()) || "";
  }
  if (!state.playerId) {
    closePage();
    openView("view-game");
    toast(wt("enter_id_first"));
    return;
  }
  let ok = 0, fail = 0;
  for (const item of state.cart) {
    const res = await api("/api/order", {
      game_id: item.gameId,
      package_id: item.pkgId,
      player_id: state.playerId,
      method: "balance",
    });
    if (res.ok && res.order_id) ok++;
    else fail++;
    if (res.ok && res.order_id) {
      state.user.balance = (state.user.balance || 0) - item.price;
    }
  }
  state.cart = [];
  updateCartBadge();
  saveCartCloud();
  renderUser();
  closePage();
  haptic(fail ? "error" : "success");
  if (!fail) {
    pulseBalance();
    successBurst();
    confettiBurst(24);
  }
  toast(fail ? wt("batch_result", ok, fail) : wt("batch_ok", ok));
}

/* ---------------- TOPUP ---------------- */
const PAY_METHODS = [
  { id: "stars", name: "Telegram Stars", ico: "⭐️" },
  { id: "paynet", name: "PAYNET", ico: "💳" },
  { id: "uzqr", name: "UzQR Tezkor", nkey: "pay_uzqr", ico: "📲" },
  { id: "card", name: "Karta", nkey: "pay_by_card", ico: "💳" },
];
function pmName(m) { return m ? (m.nkey ? wt(m.nkey) : m.name) : ""; }
const AMOUNTS = [10000, 25000, 50000, 100000, 200000, 500000];

function renderTopup() {
  state.payMethod = state.payMethod || "stars";
  document.getElementById("topup-method-label").textContent =
    pmName(PAY_METHODS.find((m) => m.id === state.payMethod)) || "Stars";
  const mg = document.getElementById("methods-grid");
  mg.innerHTML = "";
  PAY_METHODS.forEach((m) => {
    const chip = document.createElement("div");
    chip.className = "method-chip" + (m.id === state.payMethod ? " active" : "");
    chip.textContent = `${m.ico} ${pmName(m)}`;
    chip.onclick = () => { state.payMethod = m.id; renderTopup(); haptic("selection"); };
    mg.appendChild(chip);
  });
  document.getElementById("min-hint").textContent =
    state.payMethod === "stars" ? wt("stars_rate") : wt("min_sum", fmt(state.minTopup));
  const presets = document.getElementById("amount-presets");
  presets.innerHTML = "";
  AMOUNTS.forEach((a) => {
    const chip = document.createElement("div");
    chip.className = "amount-chip" + (state.topupAmount === a ? " active" : "");
    chip.textContent = `${fmt(a)} ${wt("sum_suffix")}`;
    chip.onclick = () => {
      state.topupAmount = a;
      document.getElementById("topup-amount").value = a;
      renderTopup();
      haptic("selection");
    };
    presets.appendChild(chip);
  });
}

async function doTopup() {
  if (state._sending) return; // double-click himoya
  let amount = state.topupAmount;
  const inp = document.getElementById("topup-amount").value.replace(/\s/g, "").replace(/,/g, "");
  if (inp) amount = parseInt(inp, 10);
  if (!amount || amount <= 0) return toast(wt("enter_amount"));
  if (amount < (state.minTopup || 3000)) return toast(wt("min_sum", fmt(state.minTopup || 3000)));

  state._sending = true;
  try {
    const res = await api("/api/topup", { method: state.payMethod, amount });
  if (!res.ok) {
    if (res.error === "maintenance") return toast(wt("maintenance_msg"));
    if (res.error === "min") return toast(wt("min_amt", fmt(res.min)));
    if (res.error === "max") return toast(wt("max_amt", fmt(res.max)));
    return toast(wt("err_generic"));
  }
  if (res.need_payment) {
    showManual({ title: "⭐️ Telegram Stars", body: wt("stars_req", fmt(amount) + " " + wt("sum_suffix")) });
    return;
  }
  if (res.need_manual) openPayTimer(res);
  } finally {
    state._sending = false;
  }
}

/* ---------------- HISTORY + PROGRESS + RATING ---------------- */
function switchHistory(btn, tab) {
  state.historyTab = tab;
  document.querySelectorAll(".htab").forEach((b) => b.classList.remove("active"));
  btn.classList.add("active");
  const list = document.getElementById("history-list");
  if (list) { list.classList.remove("tab-anim"); void list.offsetWidth; list.classList.add("tab-anim"); }
  loadHistory();
  haptic("selection");
}

function refreshHistory() { loadHistory(); toast(wt("refreshed")); }

const ORDER_STAT = {
  "kutilmoqda": ["st_pending", "st-pending"],
  "bajarildi": ["st_done", "st-done"],
  "rad_etildi": ["st_cancelled", "st-cancelled"],
  "to'lov_kutilmoqda": ["st_waitpay", "st-waitpay"],
};
const PAY_STAT = {
  "kutilmoqda": ["st_pending", "st-pending"],
  "tasdiqlandi": ["st_ok", "st-done"],
  "rad_etildi": ["st_cancelled", "st-cancelled"],
};

function progressStepsHtml(status) {
  const steps = [wt("step_created"), wt("step_paid"), wt("step_delivered")];
  let active = 0;
  if (status === "to'lov_kutilmoqda") active = 1;
  else if (status === "kutilmoqda") active = 1;
  else if (status === "bajarildi") active = 3;
  else if (status === "rad_etildi") active = -1;
  return `<div class="progress-steps">${steps.map((s, i) => {
    let cls = "";
    if (active === 3) cls = "done";
    else if (i < active) cls = "done";
    else if (i === active) cls = "active";
    if (active === -1 && i === 0) cls = "done";
    if (active === -1 && i === 1) cls = "active";
    return `<div class="pstep ${cls}"><div class="pstep-dot">${cls === "done" ? "✓" : i + 1}</div><div class="pstep-label">${s}</div></div>`;
  }).join("")}</div>`;
}

function starsHtml(orderId, rated) {
  return `<div class="rate-row" data-oid="${orderId}">${
    [1,2,3,4,5].map(n => `<span class="rate-star ${rated && n <= rated ? "on" : ""}" onclick="rateOrder(${orderId},${n})">★</span>`).join("")
  }</div>`;
}

async function rateOrder(orderId, stars) {
  const res = await api("/api/rate", { order_id: orderId, stars });
  toast(res.message || res.error || wt("err_generic"));
  if (res.ok) {
    haptic("success");
    const row = document.querySelector(`.rate-row[data-oid="${orderId}"]`);
    if (row) {
      row.querySelectorAll(".rate-star").forEach((s, i) => s.classList.toggle("on", i < stars));
    }
  } else haptic("error");
}

function showReceipt(o) {
  const body = document.getElementById("receipt-body");
  const [lk] = ORDER_STAT[o.status] || [null]; const label = lk ? wt(lk) : (o.status || "");
  body.innerHTML = `
    <div class="receipt-box">
      <div class="r-head">🧾 DONATE FM CHEK</div>
      <div class="r-row"><span class="k">${wt("order_no")}</span><span class="v">#${o.id || "—"}</span></div>
      ${o.payment_id ? `<div class="r-row"><span class="k">${wt("pay_amount")}</span><span class="v">#${o.payment_id}</span></div>` : ""}
      <div class="r-row"><span class="k">${wt("date_label")}</span><span class="v">${esc(o.created_at || new Date().toLocaleString("ru-RU"))}</span></div>
      <div class="r-row"><span class="k">${wt("game_label")}</span><span class="v">${esc(o.platform_name || "DONATE FM")}</span></div>
      <div class="r-row"><span class="k">${wt("pkg_label")}</span><span class="v">${esc(o.package_name || o.method || "—")}</span></div>
      ${o.player_id ? `<div class="r-row"><span class="k">${wt("player_lbl")}</span><span class="v">${esc(o.player_id)}</span></div>` : ""}
      <div class="r-row"><span class="k">${wt("holat")}</span><span class="v">${esc(label || o.status || "")}</span></div>
      <div class="r-row r-total"><span class="k">${wt("total_label")}</span><span class="v">${fmt(o.price || o.amount || 0)} ${wt("sum_suffix")}</span></div>
      <div class="r-foot">DONATE FM · @${esc(state.botUsername || "donatefm_bot")}<br>${wt("receipt_foot")}</div>
    </div>
    <button class="big-btn" onclick="window.print()">${wt("print_receipt")}</button>`;
  openPage("receipt-sheet");
}

async function loadHistory() {
  const list = document.getElementById("history-list");
  skeletonList(list);
  const res = await api("/api/history");
  if (!res.ok) return (list.innerHTML = emptyHtml("⚠️", wt("err_generic"), wt("err_network"), wt("try_again"), "loadHistory()"));
  list.innerHTML = "";
  list.classList.add("stagger-list");
  state.historyOrders = res.orders || [];

  if (state.historyTab === "orders") {
    if (!res.orders.length) {
      list.innerHTML = emptyHtml("📦", wt("no_orders"), wt("no_orders_yet"), "🎮 " + wt("view_games"), "openView('view-home')");
      return;
    }
    res.orders.forEach((o) => {
      const [lk, cls] = ORDER_STAT[o.status] || ["st_pending", "st-pending"]; const label = wt(lk);
      const el = document.createElement("div");
      el.className = "h-card";
      const canRate = o.status === "bajarildi";
      el.innerHTML = `
        <div class="h-status ${cls}">${label}</div>
        <div class="h-top"><span class="h-game">${esc(o.platform_name)}</span><span class="h-amount" style="color:var(--danger)">-${fmt(o.price)} ${wt("sum_suffix")}</span></div>
        <div class="h-details">${esc(o.package_name)}<br>${wt("player_lbl")} ${esc(o.player_id)}<br>${esc(o.created_at)}</div>
        ${progressStepsHtml(o.status)}
        ${canRate ? `<div style="margin-top:10px;font-size:12px;color:var(--muted);font-weight:700">${wt("baholang")}</div>${starsHtml(o.id, o.rating || 0)}` : ""}
        <div class="h-actions">
          <button class="mini-btn" onclick="showReceiptByOrder(${o.id})">🧾 ${wt("receipt")}</button>
          ${o.package_id ? `<button class="mini-btn ok" onclick="reorder(${o.id})">🔁 ${wt("reorder")}</button>` : ""}
        </div>`;
      list.appendChild(el);
    });
  } else {
    if (!res.payments.length) {
      list.innerHTML = emptyHtml("💳", wt("no_payments"), wt("no_finance"), "💳 " + wt("topup_go"), "openView('view-topup')");
      return;
    }
    res.payments.forEach((p) => {
      const [lk, cls] = PAY_STAT[p.status] || ["st_pending", "st-pending"]; const label = wt(lk);
      const pname = pmName(PAY_METHODS.find((m) => m.id === p.method)) || p.method;
      const el = document.createElement("div");
      el.className = "h-card";
      el.innerHTML = `
        <div class="h-status ${cls}">${label}</div>
        <div class="h-top"><span class="h-game">${pname}</span><span class="h-amount" style="color:var(--accent2)">+${fmt(p.amount)} ${wt("sum_suffix")}</span></div>
        <div class="h-details">${p.created_at}</div>
        <div class="h-actions"><button class="mini-btn" onclick="showReceipt({id:${p.id},payment_id:${p.id},amount:${p.amount},method:'${esc(p.method)}',created_at:'${esc(p.created_at)}',status:'${esc(p.status)}'})">🧾 ${wt("receipt")}</button></div>`;
      list.appendChild(el);
    });
  }
}

async function showReceiptByOrder(orderId) {
  const o = state.historyOrders.find(x => x.id === orderId);
  if (o) showReceipt(o);
}

async function reorder(orderId) {
  const res = await api("/api/reorder", { order_id: orderId });
  if (res.ok && res.order_id) {
    toast(wt("reorder_ok"));
    haptic("success");
    state.user.balance = res.balance;
    renderUser();
    if (activeViewId() === "view-history") loadHistory();
  } else {
    toast(res.message || res.error || wt("err_generic"));
    haptic("error");
  }
}

/* Tez qayta buyurtma: o'yin ichida oxirgi buyurtmani takrorlash */
let lastOrderId = 0;

async function loadLastOrder(gameId) {
  const bar = document.getElementById("repeat-bar");
  if (!bar) return;
  bar.style.display = "none";
  lastOrderId = 0;
  const res = await api("/api/last_order", { game_id: gameId });
  if (res.ok && res.order) {
    lastOrderId = res.order.id;
    const sub = document.getElementById("repeat-sub");
    if (sub) sub.textContent = `#${res.order.id} · ${res.order.package_name} — ${fmt(res.order.price)} ${wt("sum_suffix")}`;
    bar.style.display = "flex";
  }
}

async function repeatLastOrder() {
  if (!lastOrderId) return;
  const btn = document.getElementById("repeat-btn");
  if (btn) btn.disabled = true;
  try {
    await reorder(lastOrderId);
  } finally {
    if (btn) btn.disabled = false;
  }
}

/* ---------------- SETTINGS ---------------- */
async function refreshProfile() {
  const res = await api("/api/init");
  if (!res.ok) return toast(res.message || res.error || wt("err_generic"));
  state.user = res.user;
  if (res.games) state.games = res.games;
  if (res.favorites) state.favorites = res.favorites;
  if (res.cards_list) state.cardsList = res.cards_list;
  renderUser();
  renderSettings();
  renderHome();
  renderGameFilterBar();
  loadHistory();
  toast(wt("refreshed"));
  haptic("success");
}

function renderSettings() {
  if (!state.user) return;
  document.getElementById("set-name").textContent = state.user.full_name || state.user.username || wt("user_label");
  document.getElementById("set-userid").textContent = state.user.id;
  countUp(document.getElementById("set-balance"), state.user.balance);
  countUp(document.getElementById("set-keshbek"), state.user.keshbek || 0);
  const phone = document.getElementById("set-phone");
  if (phone.value === "" || phone.value === "0") phone.value = state.user.phone || "";
  const labels = { uz: "O'zbekcha", ru: "Русский", en: "English" };
  document.querySelectorAll(".lbtn").forEach((b) => {
    const t = b.textContent.trim();
    b.classList.toggle("active", t === labels[state.user.lang] || (state.user.lang === "uz" && t === "O'zbekcha"));
  });
  // theme toggle reflect
  const tt = document.getElementById("theme-toggle");
  if (tt) tt.setAttribute("data-theme-state", state.theme);
  const ta = document.getElementById("theme-auto");
  if (ta) ta.classList.toggle("active", state.themeMode === "auto");
}

async function savePhone() {
  const val = document.getElementById("set-phone").value.trim();
  if (!val) return toast(wt("enter_number"));
  const res = await api("/api/save_phone", { phone: val });
  if (res.ok) { state.user.phone = val; toast(wt("saved_ok")); haptic("success"); }
}

async function setLang(lang) {
  const res = await api("/api/save_lang", { lang });
  if (res.ok) {
    state.user.lang = lang;
    currentLang = lang;
    hydrateI18n();
    renderUser();
    renderHome();
    renderSettings();
    if (activeViewId() === "view-history") loadHistory();
    if (topPage() && topPage().id === "referral-sheet") loadReferral();
    haptic("success");
    toast(lang === "en" ? "Language: English" : lang === "ru" ? "Язык: Русский" : "Til: O'zbekcha");
  } else toast(res.message || wt("err_generic"));
}

function openSupport() {
  const un = (state.supportUsername || state.botUsername || "").replace(/^@/, "");
  if (un) {
    if (tg) tg.openTelegramLink(`https://t.me/${un}`);
    else window.open(`https://t.me/${un}`, "_blank");
  } else toast(wt("support_not_found"));
}

/* ---------------- REFERRAL / PROMO / LEADERBOARD ---------------- */
function openReferral() {
  openPage("referral-sheet");
  loadReferral();
}

function openInviteWeb() { openReferral(); }

async function loadReferral() {
  const res = await api("/api/referral");
  if (!res.ok) return;
  state.inviteLink = res.link;
  document.getElementById("ref-link").value = res.link;
  document.getElementById("ref-count").textContent = res.count;
  document.getElementById("ref-reward").textContent = `${fmt(res.total_reward)} ${wt("sum_suffix")}`;
  document.getElementById("ref-percent").textContent = `${res.percent}%`;
}

function copyRef() {
  const el = document.getElementById("ref-link");
  el.select();
  try { navigator.clipboard.writeText(el.value); toast(wt("copied")); }
  catch (e) { toast(wt("link_prefix") + el.value); }
  haptic("success");
}

function shareRef() {
  if (!state.inviteLink) { loadReferral(); return toast(wt("loading")); }
  const url = `https://t.me/share/url?url=${encodeURIComponent(state.inviteLink)}&text=${encodeURIComponent("Donate FM do'koniga xush kelibsiz! O'yinlarni arzon narxda oling.")}`;
  if (tg) {
    try { tg.openTelegramLink(url); } catch (e) { window.open(url, "_blank"); }
  } else window.open(url, "_blank");
  closePage();
}

function openPromo() {
  document.getElementById("promo-input").value = "";
  openPage("promo-sheet");
}

async function applyPromo() {
  const code = document.getElementById("promo-input").value.trim();
  if (!code) return toast(wt("enter_promo"));
  const res = await api("/api/promo", { code });
  if (res.ok) {
    toast("🎉 " + res.message);
    countUp(document.getElementById("balance-banner"), res.balance, " " + wt("sum_suffix"));
    state.user.balance = res.balance;
    renderUser();
    pulseBalance();
    confettiBurst(20);
    closePage();
    haptic("success");
  } else {
    toast(res.message || wt("promo_bad"));
    haptic("error");
  }
}

function openLeaderboard() {
  openPage("lb-sheet");
  loadLeaderboard();
}

async function loadLeaderboard() {
  const wrap = document.getElementById("lb-list");
  wrap.innerHTML = `<div class="sk sk-card"></div><div class="sk sk-card"></div><div class="sk sk-card"></div>`;
  const res = await api("/api/ref_leaderboard");
  if (!res.ok) return (wrap.innerHTML = emptyHtml("⚠️", wt("err_generic"), wt("err_load")));
  if (!res.board || !res.board.length) {
    wrap.innerHTML = emptyHtml("🏆", wt("no_rating"), wt("be_first"));
    return;
  }
  wrap.innerHTML = res.board.map((r, i) => `
    <div class="lb-item ${i === 0 ? "top1" : i === 1 ? "top2" : i === 2 ? "top3" : ""}" style="animation-delay:${i * 0.05}s">
      <div class="lb-rank">${i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : i + 1}</div>
      <div class="lb-info">
        <div class="lb-name">${esc(r.full_name || r.username || "User " + r.user_id)}</div>
        <div class="lb-sub">👥 ${r.invites} ta taklif</div>
      </div>
      <div class="lb-val">${fmt(r.reward)} ${wt("sum_suffix")}</div>
    </div>`).join("");
}

/* ---------------- NOTIFICATIONS ---------------- */
async function openNotifications() {
  openPage("notif-sheet");
  const wrap = document.getElementById("notif-list");
  wrap.innerHTML = `<div class="sk sk-card"></div><div class="sk sk-card"></div><div class="sk sk-card"></div>`;
  const res = await api("/api/notifications");
  if (!res.ok) return (wrap.innerHTML = emptyHtml("⚠️", wt("err_generic"), wt("err_load")));
  if (!res.notifications || !res.notifications.length) {
    wrap.innerHTML = emptyHtml("🔕", wt("no_notifications"), wt("new_msgs_here"));
    return;
  }
  wrap.innerHTML = res.notifications.map((n, i) => {
    const unread = !n.is_read;
    const ico = (n.text || "").includes("bonus") || (n.text || "").includes("Referral") ? "🎁"
      : (n.text || "").includes("Keshbek") ? "💎"
      : (n.text || "").includes("rad") || (n.text || "").includes("Rad") ? "❌"
      : (n.text || "").includes("bajar") || (n.text || "").includes("✅") ? "✅" : "🔔";
    const plain = String(n.text || "").replace(/<[^>]+>/g, "");
    return `<div class="notif-item ${unread ? "unread" : ""}" style="animation-delay:${i * 0.04}s">
      <span class="notif-ico">${ico}</span>
      <div class="notif-body">
        <div>${esc(plain)}</div>
        <div class="notif-time">${esc(n.created_at || "")}</div>
      </div>
    </div>`;
  }).join("");
}

async function markAllRead() {
  const res = await api("/api/notifications", { mark_read: true });
  if (res.ok) {
    state.unreadNotifs = 0;
    updateNotifBadge();
    openNotifications();
    haptic("success");
    toast(wt("all_read_ok"));
  }
}

function updateNotifBadge() {
  const b = document.getElementById("notif-badge");
  if (!b) return;
  if (state.unreadNotifs > 0) { b.style.display = "flex"; b.textContent = state.unreadNotifs > 99 ? "99+" : state.unreadNotifs; }
  else b.style.display = "none";
}

/* ---------------- ADMIN PANEL ---------------- */
function stagReveal(root) {
  if (!root) return;
  const deep = root.querySelectorAll(
    ":scope > .stat-grid > .stat-card, " +
    ":scope > #admin-orders-list > .h-card, " +
    ":scope > #admin-users-list > .h-card, " +
    ":scope > #admin-pay-list > .h-card, " +
    ":scope > .games-grid > .game-card"
  );
  let i = 0;
  const mark = (el) => {
    if (el.dataset.staged) return;
    el.dataset.staged = "1";
    el.style.opacity = "1";
    el.style.animationDelay = Math.min(i * 0.05, 0.55) + "s";
    el.classList.add("reveal-up");
    i++;
  };
  root.querySelectorAll(":scope > *").forEach((el) => {
    if (
      el.classList.contains("stat-grid") ||
      el.classList.contains("games-grid") ||
      el.classList.contains("sk") ||
      el.classList.contains("sk-card") ||
      el.id === "admin-orders-list" ||
      el.id === "admin-users-list" ||
      el.id === "admin-pay-list"
    ) return;
    mark(el);
  });
  deep.forEach(mark);
}

function switchAdmin(tab) {
  state.adminTab = tab;
  document.querySelectorAll(".atab").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  const content = document.getElementById("admin-content");
  if (content) { content.classList.remove("tab-anim"); void content.offsetWidth; content.classList.add("tab-anim"); }
  const p = loadAdmin();
  if (p && typeof p.then === "function") p.then(() => stagReveal(content)).catch(() => {});
  setTimeout(() => { if (content) stagReveal(content); }, 650);
  haptic("selection");
}

async function loadAdmin() {
  const content = document.getElementById("admin-content");
  if (!state.isAdmin) {
    content.innerHTML = emptyHtml("🔒", wt("no_admin_rights"), wt("only_admins"));
    return;
  }
  // Race guard: kechikkan eski tab yozuvi yangi tabni bosmasin
  const seq = (state.adminSeq = (state.adminSeq || 0) + 1);
  const c = new Proxy(content, {
    get(t, k) {
      const v = t[k];
      return typeof v === "function" ? v.bind(t) : v;
    },
    set(t, k, v) {
      if ((state.adminSeq || 0) !== seq) return true;
      t[k] = v;
      return true;
    },
  });
  if (state.adminTab === "dash") return loadAdminDash(c);
  if (state.adminTab === "orders") return loadAdminOrders(c);
  if (state.adminTab === "payments") return loadAdminPayments(c);
  if (state.adminTab === "users") return loadAdminUsers(c);
  if (state.adminTab === "promos") return loadAdminPromos(c);
  if (state.adminTab === "games") return loadAdminGames(c);
  if (state.adminTab === "broadcast") return loadAdminBroadcast(c);
  if (state.adminTab === "settings") return loadAdminSettings(c);
  if (state.adminTab === "audit") return loadAdminAudit(c);
}

/* Sparkline SVG */
function sparklineSvg(series, key = "revenue") {
  if (!series || !series.length) return "";
  const vals = series.map(s => Number(s[key]) || 0);
  const max = Math.max(...vals, 1);
  const min = 0;
  const W = 300, H = 64, pad = 4;
  const pts = vals.map((v, i) => {
    const x = pad + (i / Math.max(1, vals.length - 1)) * (W - pad * 2);
    const y = H - pad - ((v - min) / (max - min || 1)) * (H - pad * 2);
    return [x, y];
  });
  const line = pts.map(p => p.join(",")).join(" ");
  const area = `${pts[0][0]},${H} ${line} ${pts[pts.length - 1][0]},${H}`;
  const last = pts[pts.length - 1];
  return `
  <svg class="sparkline" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">
    <defs>
      <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="var(--accent2)" stop-opacity="0.55"/>
        <stop offset="100%" stop-color="var(--accent2)" stop-opacity="0"/>
      </linearGradient>
    </defs>
    <polygon class="area" points="${area}"/>
    <polyline class="line" points="${line}" pathLength="1"/>
    <circle class="dot" cx="${last[0]}" cy="${last[1]}" r="4"/>
  </svg>
  <div class="spark-labels">${series.map(s => `<span>${s.day.slice(5)}</span>`).join("")}</div>`;
}

async function loadAdminDash(content) {
  content.innerHTML = `<div class="sk sk-card" style="height:140px"></div><div class="sk sk-card" style="height:180px"></div><div class="sk sk-card" style="height:120px"></div>`;
  const [statsRes, chartRes, refRes] = await Promise.all([
    api("/api/admin/stats"),
    api("/api/admin/chart"),
    api("/api/admin/refstats"),
  ]);
  if (!statsRes.ok) return (content.innerHTML = emptyHtml("⚠️", wt("err_generic"), wt("err_load")));
  const refBlock = refRes && refRes.ok && (refRes.referrers || []).length
    ? `<div class="admin-section">
      <div class="as-title">${wt("ref_top_title")}</div>
      ${refRes.referrers.map((r) => `<div class="as-row" style="font-size:13px">👤 <b>${esc(r.full_name || r.username || r.user_id)}</b>${r.username ? " @" + esc(r.username) : ""} · ${wt("ref_invites")}: <b>${r.invites}</b> · ${wt("ref_earned")}: <b>${fmt(r.reward)} ${wt("sum_suffix")}</b></div>`).join("")}
    </div>` : "";
  const s = statsRes.stats;
  const series = chartRes.ok ? chartRes.series : [];
  const totalRev7 = series.reduce((a, x) => a + (x.revenue || 0), 0);

  content.innerHTML = `
    <div class="spark-wrap">
      <div class="spark-title"><span>${wt("week_revenue")}</span><span class="sub">${fmt(totalRev7)} ${wt("sum_suffix")}</span></div>
      ${series.length ? sparklineSvg(series, "revenue") : `<div class="h-empty" style="padding:20px">${wt("no_data")}</div>`}
    </div>
    <div class="spark-wrap">
      <div class="spark-title"><span>${wt("week_topups")}</span><span class="sub">${fmt(series.reduce((a,x)=>a+(x.topups||0),0))} ${wt("sum_suffix")}</span></div>
      ${series.length ? sparklineSvg(series, "topups") : ""}
    </div>
    <div class="mb-4 stat-grid">
      <div class="stat-card"><div class="sc-val" data-count="${s.users}">${fmt(s.users)}</div><div class="sc-label">${wt("stat_total_users")}</div></div>
      <div class="stat-card accent"><div class="sc-val" data-count="${s.month_users}">${fmt(s.month_users)}</div><div class="sc-label">${wt("stat_mau")}</div></div>
      <div class="stat-card ok"><div class="sc-val" data-count="${s.month_new_users}">${fmt(s.month_new_users)}</div><div class="sc-label">${wt("stat_new_users")}</div></div>
      <div class="stat-card"><div class="sc-val" data-count="${s.orders_done}">${fmt(s.orders_done)}</div><div class="sc-label">${wt("stat_done")}</div></div>
      <div class="stat-card accent"><div class="sc-val" data-count="${s.revenue}">${fmt(s.revenue)}</div><div class="sc-label">${wt("stat_revenue")}</div></div>
      <div class="stat-card accent"><div class="sc-val" data-count="${s.month_revenue}">${fmt(s.month_revenue)}</div><div class="sc-label">${wt("stat_month_rev")}</div></div>
      <div class="stat-card"><div class="sc-val" data-count="${s.topups}">${fmt(s.topups)}</div><div class="sc-label">${wt("stat_topupped")}</div></div>
      <div class="stat-card"><div class="sc-val" data-count="${s.month_topups}">${fmt(s.month_topups)}</div><div class="sc-label">${wt("stat_month_topups")}</div></div>
      <div class="stat-card warn"><div class="sc-val" data-count="${s.pending_orders}">${fmt(s.pending_orders)}</div><div class="sc-label">${wt("stat_pending")}</div></div>
      <div class="stat-card danger"><div class="sc-val" data-count="${s.pending_payments}">${fmt(s.pending_payments)}</div><div class="sc-label">${wt("stat_waitpay")}</div></div>
    </div>
    <div class="admin-section">
      <div class="as-title">${wt("today_title")}</div>
      <div class="as-row">${wt("today_done_orders")} <b>${fmt(s.today_orders)}</b></div>
    </div>
    <div class="admin-section">
      <div class="as-title">${wt("autodel_title")}</div>
      <div class="as-row">${wt("provider")}: <b>${esc(statsRes.delivery.provider)}</b></div>
      <div class="as-row">${wt("interval")}: <b>${statsRes.delivery.interval} sek</b></div>
      <div class="as-row">API: <code>${esc(statsRes.delivery.api_url || "—")}</code></div>
    </div>
    <div class="admin-section">
      <div class="as-title">${wt("settings_title")}</div>
      <div class="as-row">${wt("active_card")}: <b>${esc(statsRes.settings.card_active)}</b></div>
      <div class="as-row">1000 Stars: <b>${fmt(statsRes.settings.star_rate_1000)} ${wt("sum_suffix")}</b></div>
      <div class="as-row">${wt("cashback")}: <b>${statsRes.settings.keshbek_percent}%</b></div>
      <div class="as-row">${wt("referral_word")}: <b>${statsRes.settings.referral_percent}%</b></div>
      <div class="as-row">${wt("min_max_topup")}: <b>${fmt(statsRes.settings.min_topup_card)} / ${fmt(statsRes.settings.max_topup_card)} ${wt("sum_suffix")}</b></div>
    </div>${refBlock}`;
  // animate counts
  content.querySelectorAll("[data-count]").forEach(el => {
    countUp(el, Number(el.dataset.count));
  });
}

const ORDER_FILTERS = [
  ["kutilmoqda", "fl_pending"],
  ["bajarildi", "fl_done"],
  ["rad_etildi", "fl_rejected"],
  ["", "fl_all"],
];

async function loadAdminOrders(content) {
  content.innerHTML = `
    <div class="seg-tabs">
      ${ORDER_FILTERS.map(([v, n]) =>
        `<button class="seg" data-f="${v}" onclick="setOrderFilter('${v}')">${wt(n)}</button>`).join("")}
      <button class="seg" style="margin-left:auto" onclick="adminExport('orders')">${wt("export_csv")}</button>
    </div>
    <div id="admin-orders-list"><div class="sk sk-card"></div><div class="sk sk-card"></div></div>`;
  content.querySelectorAll(".seg").forEach((b) => b.classList.toggle("active", b.dataset.f === state.adminOrderFilter));
  await renderAdminOrders();
}

function setOrderFilter(f) {
  state.adminOrderFilter = f;
  document.querySelectorAll("#admin-content .seg").forEach((b) => b.classList.toggle("active", b.dataset.f === f));
  renderAdminOrders();
  haptic("selection");
}

async function renderAdminOrders() {
  const wrap = document.getElementById("admin-orders-list");
  if (!wrap) return;
  skeletonList(wrap);
  const res = await api("/api/admin/orders", { status: state.adminOrderFilter, limit: 50 });
  if (!res.ok) return (wrap.innerHTML = emptyHtml("⚠️", wt("err_generic"), wt("err_load")));
  wrap.classList.add("stagger-list");
  if (!res.orders.length) {
    wrap.innerHTML = emptyHtml("✅", wt("no_orders"), wt("no_filter_rows"));
    return;
  }
  const STAT = {
    "kutilmoqda": ["⏳ " + wt("st_pending"), "st-pending"],
    "bajarildi": [wt("btn_done"), "st-done"],
    "rad_etildi": [wt("st_reject_short"), "st-cancelled"],
    "to'lov_kutilmoqda": ["💳 " + wt("stat_waitpay"), "st-waitpay"],
  };
  wrap.innerHTML = "";
  res.orders.forEach((o) => {
    const [label, cls] = STAT[o.status] || [esc(o.status), "st-pending"];
    const el = document.createElement("div");
    el.className = "h-card";
    el.innerHTML = `
      <div class="h-status ${cls}">${label}</div>
      <div class="h-top"><span class="h-game">#${o.id} ${esc(o.platform_name)}</span><span class="h-amount">${fmt(o.price)} ${wt("sum_suffix")}</span></div>
      <div class="h-details">${esc(o.package_name)}<br>${wt("player_lbl")}: <b>${esc(o.player_id)}</b><br>${wt("client_word")}: ${o.user_id}<br>${esc(o.created_at)}</div>
      <div class="admin-actions">
        ${o.status === "kutilmoqda" ? `
          <button class="mini-btn ok" onclick="adminOrder('${o.id}','ok')">✅ ${wt("st_done")}</button>
          <button class="mini-btn danger" onclick="adminOrder('${o.id}','refund','${fmt(o.price)}')">↩️ ${wt("refund_word")}</button>` : ""}
        ${o.status === "bajarildi" ? `<button class="mini-btn" onclick="adminOrder('${o.id}','refund','${fmt(o.price)}')">↩️ ${wt("refund_word")}</button>` : ""}
      </div>`;
    wrap.appendChild(el);
  });
  stagReveal(wrap);
}

async function adminOrder(orderId, action, price) {
  if (action === "refund") {
    const ok = await confirmDialog(wt("cf_order_reject", orderId), wt("cf_refund", price || ""));
    if (!ok) return;
  }
  const res = await api("/api/admin/order_action", { order_id: orderId, action });
  toast(res.message || res.error || wt("err_generic"));
  haptic(res.ok ? "success" : "error");
  renderAdminOrders();
}

async function loadAdminPayments(content) {
  content.innerHTML = `
    <div class="seg-tabs">
      <button class="seg ${!state.adminPayAll ? "active" : ""}" onclick="setPayFilter(false)">${wt("fl_pending")}</button>
      <button class="seg ${state.adminPayAll ? "active" : ""}" onclick="setPayFilter(true)">${wt("fl_all")}</button>
      <button class="seg" style="margin-left:auto" onclick="adminExport('payments')">${wt("export_csv")}</button>
    </div>
    <div id="admin-pay-list"><div class="sk sk-card"></div><div class="sk sk-card"></div></div>`;
  await renderAdminPayments();
}

function setPayFilter(all) {
  state.adminPayAll = all;
  document.querySelectorAll("#admin-content .seg").forEach((b, i) =>
    b.classList.toggle("active", all ? i === 1 : i === 0));
  renderAdminPayments();
  haptic("selection");
}

async function renderAdminPayments() {
  const wrap = document.getElementById("admin-pay-list");
  if (!wrap) return;
  skeletonList(wrap);
  const res = await api("/api/admin/payments", { all: state.adminPayAll });
  if (!res.ok) return (wrap.innerHTML = emptyHtml("⚠️", wt("err_generic"), wt("err_load")));
  if (!res.payments.length) {
    wrap.innerHTML = emptyHtml("✅", wt("no_payments"), wt("no_waiting_pay"));
    return;
  }
  const PST = {
    "kutilmoqda": ["⏳ " + wt("st_pending"), "st-pending"],
    "tasdiqlandi": ["✅ " + wt("st_confirmed"), "st-done"],
    "rad_etildi": ["❌ " + wt("st_rejected"), "st-cancelled"],
    "qaytarildi": ["↩️ " + wt("st_refunded"), "st-cancelled"],
  };
  wrap.innerHTML = "";
  res.payments.forEach((p) => {
    const pname = { card: wt("method_card"), paynet: "PAYNET", uzqr: wt("pay_uzqr"), stars: "Stars", refund: wt("method_refund") }[p.method] || p.method;
    const [label, cls] = PST[p.status] || [esc(p.status), "st-pending"];
    const el = document.createElement("div");
    el.className = "h-card";
    el.innerHTML = `
      <div class="h-status ${cls}">${label}</div>
      <div class="h-top"><span class="h-game">#${p.id} ${esc(pname)}</span><span class="h-amount" style="color:var(--accent2)">${fmt(p.amount)} ${wt("sum_suffix")}</span></div>
      <div class="h-details">${wt("client_word")}: ${p.user_id}${p.ref ? `<br>Ref: <code>${esc(p.ref)}</code>` : ""}<br>${esc(p.created_at)}</div>
      ${(p.status === "kutilmoqda" || p.status === "rad_etildi") ? `
      <div class="admin-actions">
        <button class="mini-btn ok" onclick="adminPay('${p.id}','ok')">${wt("confirm_pay")}</button>
        ${p.status === "kutilmoqda" ? `<button class="mini-btn danger" onclick="adminPay('${p.id}','no')">❌ ${wt("st_rejected")}</button>` : ""}
        <button class="mini-btn danger" onclick="adminToggleBan(${p.user_id},1)">🚫 ${wt("adm_ban")}</button>
      </div>` : ""}`;
    wrap.appendChild(el);
  });
  stagReveal(wrap);
}

async function adminPay(paymentId, action) {
  if (action === "no") {
    const ok = await confirmDialog(wt("cf_pay_reject", paymentId), wt("refund_note"));
    if (!ok) return;
  }
  const res = await api("/api/admin/payment_action", { payment_id: paymentId, action });
  toast(res.message || res.error || wt("err_generic"));
  haptic(res.ok ? "success" : "error");
  renderAdminPayments();
}

async function loadAdminUsers(content) {
  const res = await api("/api/admin/users");
  if (!res.ok) return (content.innerHTML = emptyHtml("⚠️", wt("err_generic"), wt("err_load")));
  content.innerHTML = `
    <div class="admin-search">
      <input type="text" id="admin-search-input" placeholder="${wt("admin_search_ph")}" onkeydown="if(event.key==='Enter')adminSearch()">
      <button class="mini-btn" onclick="adminSearch()">${wt("search_btn")}</button>
    </div>
    <div id="admin-users-list"></div>`;
  renderAdminUsers(res.users);
}

async function adminSearch() {
  const q = document.getElementById("admin-search-input").value.trim();
  const res = await api("/api/admin/users", { query: q });
  if (!res || !Array.isArray(res.users)) {
    const wrap = document.getElementById("admin-users-list");
    if (wrap) wrap.innerHTML = emptyHtml("⚠️", wt("err_generic"), wt("err_load"));
    return;
  }
  renderAdminUsers(res.users);
}

function renderAdminUsers(users) {
  const wrap = document.getElementById("admin-users-list");
  if (!wrap) return;
  if (!users || !Array.isArray(users)) { adminSearch(); return; }
  if (!users.length) { wrap.innerHTML = emptyHtml("🔍", wt("not_found"), wt("try_other_req")); return; }
  wrap.innerHTML = "";
  users.forEach((u) => {
    const el = document.createElement("div");
    el.className = "h-card";
    const banned = u.is_banned ? `<span class="h-status st-cancelled">${wt("banned_label")}</span>` : "";
    el.innerHTML = `
      ${banned}
      <div class="h-top"><span class="h-game">${esc(u.full_name || u.username || u.id)}</span><span class="h-amount">${fmt(u.balance)} ${wt("sum_suffix")}</span></div>
      <div class="h-details">ID: ${u.id}${u.username ? " · @" + esc(u.username) : ""}<br>${wt("total_topped_up")}: ${fmt(u.total_topup)} ${wt("sum_suffix")}</div>
      <div class="admin-actions">
        <button class="mini-btn" onclick="adminBalance(${u.id},'plus')">${wt("btn_add_bal")}</button>
        <button class="mini-btn" onclick="adminBalance(${u.id},'minus')">${wt("btn_deduct")}</button>
        <button class="mini-btn ${u.is_banned ? "ok" : "danger"}" onclick="adminToggleBan(${u.id},${u.is_banned ? 0 : 1})">${u.is_banned ? wt("btn_unban") : wt("adm_ban")}</button>
      </div>`;
    wrap.appendChild(el);
  });
  stagReveal(wrap);
}

async function adminToggleBan(userId, ban) {
  const ok = await confirmDialog(ban ? wt("cf_ban") : wt("cf_unban"));
  if (!ok) return;
  const res = await api("/api/admin/user_action", { user_id: userId, action: ban ? "ban" : "unban" });
  toast(res.message || wt("err_generic"));
  haptic(res.ok ? "success" : "error");
  adminSearch();
}

function openBalanceModal(userId, action) {
  const title = action === "plus" ? wt("adm_bal_plus") : wt("adm_bal_minus");
  const input = document.getElementById("modal-input");
  input.value = "";
  document.getElementById("modal-title").textContent = title;
  document.getElementById("modal-text").textContent = wt("sum_prompt");
  input.style.display = "block";
  document.getElementById("modal-overlay").classList.add("show");
  input.focus();

  return new Promise((resolve) => {
    const okBtn = document.getElementById("modal-ok");
    const cancelBtn = document.getElementById("modal-cancel");
    const close = () => {
      document.getElementById("modal-overlay").classList.remove("show");
      input.style.display = "none";
      okBtn.onclick = null;
      cancelBtn.onclick = null;
    };
    okBtn.onclick = () => {
      const amount = parseInt(input.value.replace(/\s|,/g, ""), 10);
      close();
      if (!amount || amount <= 0) { toast(wt("wrong_amount")); resolve(false); return; }
      resolve({ amount });
    };
    cancelBtn.onclick = () => { close(); resolve(false); };
  });
}

async function adminBalance(userId, action) {
  const res = await openBalanceModal(userId, action);
  if (!res) return;
  const apiRes = await api("/api/admin/user_action", { user_id: userId, action, amount: res.amount });
  toast(apiRes.message || apiRes.error || wt("err_generic"));
  haptic(apiRes.ok ? "success" : "error");
  if (apiRes.ok) adminSearch();
}

/* Admin promos */
async function loadAdminPromos(content) {
  content.innerHTML = `
    <div class="admin-section" style="margin-top:0">
      <div class="as-title">${wt("new_promo_title")}</div>
      <div class="admin-search" style="margin-top:8px">
        <input type="text" id="promo-code-in" placeholder="${wt("code_example")}">
        <input type="text" id="promo-amt-in" placeholder="${wt("amount")}" inputmode="numeric" style="max-width:100px">
        <button class="mini-btn ok" onclick="adminCreatePromo()">${wt("create_btn")}</button>
      </div>
    </div>
    <div id="admin-promo-list"><div class="sk sk-card"></div></div>`;
  const res = await api("/api/admin/promos");
  const wrap = document.getElementById("admin-promo-list");
  if (!res.ok) return (wrap.innerHTML = emptyHtml("⚠️", wt("err_generic"), wt("err_load")));
  if (!res.promos || !res.promos.length) {
    wrap.innerHTML = emptyHtml("🎁", wt("no_promo"), wt("create_promo_first"));
    return;
  }
  wrap.innerHTML = res.promos.map((p, i) => `
    <div class="promo-item" style="animation-delay:${i * 0.04}s">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
        <b style="font-size:15px;color:var(--accent2);letter-spacing:1px">${esc(p.code)}</b>
        <button class="mini-btn danger" style="padding:7px 12px" onclick="adminDeletePromo('${esc(p.code)}')">${wt("delete_btn")}</button>
      </div>
      <div class="audit-meta">
        <span>💰 ${fmt(p.reward_amount)} ${wt("sum_suffix")}</span>
        <span>${wt("uses_label")}: ${p.used_count || 0}/${p.max_uses || "∞"}</span>
        ${p.expires_at ? `<span>📅 ${esc(p.expires_at)}</span>` : ""}
      </div>
    </div>`).join("");
}

async function adminCreatePromo() {
  const code = document.getElementById("promo-code-in")?.value.trim();
  const amt = parseInt(document.getElementById("promo-amt-in")?.value.replace(/\s/g, "") || "", 10);
  if (!code) return toast(wt("enter_code"));
  if (!amt || amt <= 0) return toast(wt("enter_amount"));
  const res = await api("/api/admin/promo_create", { code, amount: amt, max_uses: 100 });
  toast(res.message || res.error || wt("err_generic"));
  if (res.ok) { haptic("success"); loadAdminPromos(document.getElementById("admin-content")); }
  else haptic("error");
}

async function adminDeletePromo(code) {
  const ok = await confirmDialog(wt("cf_promo_del", code), "");
  if (!ok) return;
  const res = await api("/api/admin/promo_delete", { code });
  toast(res.message || res.error || wt("err_generic"));
  if (res.ok) loadAdminPromos(document.getElementById("admin-content"));
}

/* Admin games */
async function loadAdminGames(content) {
  content.innerHTML = `
    <div class="admin-section" style="margin-top:0">
      <div class="as-title">${wt("add_game_btn")}</div>
      <div class="admin-search" style="margin-top:8px">
        <input type="text" id="game-new-id" placeholder="${wt("game_id_ph")}">
        <input type="text" id="game-new-name" placeholder="${wt("game_name_ph")}">
        <button class="mini-btn ok" onclick="adminCreateGame()">${wt("save")}</button>
      </div>
    </div>
    <div id="admin-games-list"><div class="sk sk-card"></div></div>`;
  const res = await api("/api/admin/games");
  const wrap = document.getElementById("admin-games-list");
  if (!res.ok) return (wrap.innerHTML = emptyHtml("⚠️", wt("err_generic"), wt("err_load")));
  state.adminGames = res.games || [];
  if (!state.adminGames.length) {
    wrap.innerHTML = emptyHtml("🎮", wt("no_games"), wt("add_game_btn"));
    return;
  }
  wrap.innerHTML = state.adminGames.map((g, i) => `
    <div class="promo-item" style="animation-delay:${i * 0.04}s">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
        <b style="font-size:15px">${esc(g.emoji || "🎮")} ${esc(g.name)}</b>
        <div style="display:flex;gap:6px">
          <button class="mini-btn" onclick="adminEditGame('${esc(g.id)}')">${wt("edit_word")}</button>
          <button class="mini-btn danger" onclick="adminDeleteGame('${esc(g.id)}')">${wt("delete_btn")}</button>
        </div>
      </div>
      <div class="audit-meta">
        <span>ID: <code>${esc(g.id)}</code></span>
        <span>${wt("pkg_label")}: ${(g.packages || []).length}</span>
      </div>
    </div>`).join("");
}

function pkgRowHtml(p) {
  p = p || {};
  return `<div class="pkg-row admin-search" style="margin-bottom:6px;flex-wrap:wrap">
    <input type="text" class="pkg-id" placeholder="${wt("pkg_id_ph")}" value="${esc(p.id || "")}" style="max-width:120px">
    <input type="text" class="pkg-name" placeholder="${wt("pkg_name_ph")}" value="${esc(p.name || "")}">
    <input type="text" class="pkg-amt" placeholder="${wt("pkg_amt_ph")}" value="${esc(p.amount || "")}" style="max-width:80px">
    <input type="text" class="pkg-price" inputmode="numeric" placeholder="${wt("pkg_price_ph")}" value="${p.price != null ? esc(p.price) : ""}" style="max-width:110px">
    <input type="text" class="pkg-cat" placeholder="${wt("pkg_cat_ph")}" value="${esc(p.category || "")}" style="max-width:90px">
    <button class="mini-btn danger" onclick="this.closest('.pkg-row').remove()">❌</button>
  </div>`;
}

async function adminCreateGame() {
  const id = (document.getElementById("game-new-id")?.value || "").trim();
  const name = (document.getElementById("game-new-name")?.value || "").trim();
  if (!id || !name) return toast(wt("enter_game_name"));
  if ((state.adminGames || []).some((g) => g.id === id)) return adminEditGame(id);
  state.adminGames = state.adminGames || [];
  state.adminGames.push({ id, name, emoji: "🎮", desc: "", grid_mode: false, categories: {}, packages: [] });
  adminEditGame(id);
}

function adminEditGame(id) {
  const g = (state.adminGames || []).find((x) => x.id === id);
  if (!g) return;
  const content = document.getElementById("admin-content");
  const cats = Object.entries(g.categories || {}).map(([k, v]) => `${k}=${v}`).join("\n");
  content.innerHTML = `
    <div class="admin-section" style="margin-top:0">
      <div class="as-title">${wt("games_edit_title")}</div>
      <div style="display:flex;flex-direction:column;gap:8px;margin-top:8px">
        <div class="admin-search"><input type="text" id="ge-id" value="${esc(g.id)}" readonly style="opacity:.65"></div>
        <div class="admin-search"><input type="text" id="ge-name" placeholder="${wt("game_name_ph")}" value="${esc(g.name)}"></div>
        <div class="admin-search">
          <input type="text" id="ge-emoji" placeholder="${wt("game_emoji_ph")}" value="${esc(g.emoji || "")}" style="max-width:90px">
          <input type="text" id="ge-desc" placeholder="${wt("game_desc_ph")}" value="${esc(g.desc || "")}">
        </div>
        <label style="display:flex;gap:8px;align-items:center;font-size:13px;color:var(--muted)"><input type="checkbox" id="ge-grid" ${g.grid_mode ? "checked" : ""}> grid_mode</label>
        <textarea id="ge-cats" rows="3" placeholder="key=value">${esc(cats)}</textarea>
      </div>
      <div class="as-title" style="margin-top:12px">${wt("pkg_title")}</div>
      <div id="ge-pkgs">${(g.packages || []).map((pp) => pkgRowHtml(pp)).join("")}</div>
      <button class="mini-btn" style="margin-top:8px;width:100%" onclick="document.getElementById('ge-pkgs').insertAdjacentHTML('beforeend', pkgRowHtml({}))">${wt("pkg_add_btn")}</button>
      <div style="display:flex;gap:8px;margin-top:12px">
        <button class="mini-btn ok" style="flex:1" onclick="adminSaveGame()">${wt("save")}</button>
        <button class="mini-btn" style="flex:1" onclick="loadAdminGames(document.getElementById('admin-content'))">🔙 ${wt("games")}</button>
      </div>
    </div>`;
}

async function adminSaveGame() {
  const pkgs = Array.from(document.querySelectorAll("#ge-pkgs .pkg-row"))
    .map((row) => ({
      id: row.querySelector(".pkg-id").value.trim(),
      name: row.querySelector(".pkg-name").value.trim(),
      amount: row.querySelector(".pkg-amt").value.trim(),
      price: row.querySelector(".pkg-price").value.trim(),
      category: row.querySelector(".pkg-cat").value.trim(),
    }))
    .filter((pp) => pp.id || pp.name);
  const cats = {};
  (document.getElementById("ge-cats")?.value || "").split("\n").forEach((l) => {
    const i = l.indexOf("=");
    if (i > 0) cats[l.slice(0, i).trim()] = l.slice(i + 1).trim();
  });
  const game = {
    id: (document.getElementById("ge-id")?.value || "").trim(),
    name: (document.getElementById("ge-name")?.value || "").trim(),
    emoji: (document.getElementById("ge-emoji")?.value || "").trim(),
    desc: (document.getElementById("ge-desc")?.value || "").trim(),
    grid_mode: !!document.getElementById("ge-grid")?.checked,
    categories: cats,
    packages: pkgs,
  };
  if (!game.name) return toast(wt("enter_game_name"));
  const res = await api("/api/admin/game_save", { game });
  toast(res.ok ? wt("game_saved") : res.error || wt("err_generic"));
  haptic(res.ok ? "success" : "error");
  if (res.ok) loadAdminGames(document.getElementById("admin-content"));
}

async function adminDeleteGame(id) {
  const okc = await confirmDialog(wt("cf_game_del", id), "");
  if (!okc) return;
  const res = await api("/api/admin/game_delete", { game_id: id });
  toast(res.ok ? wt("game_deleted") : res.error || wt("err_generic"));
  haptic(res.ok ? "success" : "error");
  if (res.ok) loadAdminGames(document.getElementById("admin-content"));
}

/* Admin broadcast */
function loadAdminBroadcast(content) {
  state.bcScope = "all";
  content.innerHTML = `
    <div class="admin-section" style="margin-top:0">
      <div class="as-title">${wt("bc_title")}</div>
      <textarea id="bc-text" rows="5" placeholder="${wt("bc_text_ph")}"></textarea>
      <div class="seg-tabs" style="margin-top:8px">
        <button class="seg active" data-s="all" onclick="setBcScope('all')">${wt("bc_scope_all")}</button>
        <button class="seg" data-s="user" onclick="setBcScope('user')">${wt("bc_scope_user")}</button>
      </div>
      <div class="admin-search" id="bc-user-row" style="display:none">
        <input type="text" id="bc-user-id" placeholder="${wt("bc_user_ph")}" inputmode="numeric">
      </div>
      <button class="mini-btn ok" style="width:100%;margin-top:6px" onclick="adminBroadcast()">${wt("bc_send")}</button>
      <div class="audit-meta" style="margin-top:8px"><span>${wt("bc_tg_note")}</span></div>
    </div>`;
}

function setBcScope(sc) {
  state.bcScope = sc;
  document.querySelectorAll("#admin-content .seg").forEach((b) => b.classList.toggle("active", b.dataset.s === sc));
  const row = document.getElementById("bc-user-row");
  if (row) row.style.display = sc === "user" ? "flex" : "none";
  haptic("selection");
}

async function adminBroadcast() {
  const text = (document.getElementById("bc-text")?.value || "").trim();
  if (!text) return toast(wt("bc_empty"));
  const body = { text, scope: state.bcScope || "all" };
  if (body.scope === "user") {
    const uid = parseInt((document.getElementById("bc-user-id")?.value || "").trim(), 10);
    if (!uid) return toast(wt("bc_need_user"));
    body.user_id = uid;
  }
  const okc = await confirmDialog(wt("bc_title"), text.slice(0, 200));
  if (!okc) return;
  const res = await api("/api/admin/broadcast", body);
  if (res.ok) {
    toast(body.scope === "user" ? wt("bc_sent_user") : wt("bc_sent_all", String(res.sent || 0)));
    haptic("success");
    const t = document.getElementById("bc-text");
    if (t) t.value = "";
  } else {
    const msg = { empty: wt("bc_empty"), no_user: wt("admin_no_user") }[res.error];
    toast(msg || res.error || wt("err_generic"));
    haptic("error");
  }
}

/* Admin settings + admins */
const FEATURE_ROWS = [
  { key: "auto_delivery_enabled", i18n: "f_auto_delivery" },
  { key: "ocr_enabled", i18n: "f_ocr" },
  { key: "nickname_check_enabled", i18n: "f_nickname" },
  { key: "id_validation_enabled", i18n: "f_id_validation" },
  { key: "chek_reminder_enabled", i18n: "f_chek_reminder" },
  { key: "maintenance", i18n: "maintenance_hint" },
];

async function adminToggleFeature(key) {
  const next = !(state.adminSettings && state.adminSettings[key]);
  const res = await api("/api/admin/settings_save", { settings: { [key]: next } });
  if (res.ok) {
    state.adminSettings[key] = next;
    toast(`${wt("settings_saved")} ${next ? "✅" : "❌"}`);
    haptic("success");
    loadAdminSettings(document.getElementById("admin-content") || document.body);
  } else {
    toast(res.error || wt("err_generic"));
    haptic("error");
  }
}

async function loadAdminSettings(content) {
  content.innerHTML = `<div class="sk sk-card"></div><div class="sk sk-card"></div><div class="sk sk-card"></div>`;
  const [setRes, admRes] = await Promise.all([
    api("/api/admin/settings_get"),
    api("/api/admin/admins"),
  ]);
  if (!setRes.ok) return (content.innerHTML = emptyHtml("⚠️", wt("err_generic"), wt("err_load")));
  const st = setRes.settings;
  const adm = admRes.ok ? admRes : { admins: [], base_admins: [] };
  state.adminSettings = st;
  state.maintenance = !!st.maintenance;
  content.innerHTML = `
    <div class="admin-section" style="margin-top:0">
      <div class="as-title">${wt("settings_title")}</div>
      <div class="set-grid">
        <label>${wt("cashback")} %<input type="text" id="set_keshbek" inputmode="numeric" value="${st.keshbek_percent}"></label>
        <label>${wt("set_referral")}<input type="text" id="set_ref" inputmode="numeric" value="${st.referral_reward_topup_percent}"></label>
        <label>${wt("set_star_rate")}<input type="text" id="set_star" inputmode="numeric" value="${st.star_rate_1000}"></label>
        <label>${wt("set_min_topup")}<input type="text" id="set_min" inputmode="numeric" value="${st.min_topup_card}"></label>
        <label>${wt("set_max_topup")}<input type="text" id="set_max" inputmode="numeric" value="${st.max_topup_card}"></label>
        <label>${wt("set_daily_bonus")}<input type="text" id="set_bonus" inputmode="numeric" value="${st.daily_bonus_amount || 5000}"></label>
        <label>${wt("set_pay_window")}<input type="text" id="set_window" inputmode="numeric" value="${st.pay_window_seconds}"></label>
        <label>${wt("set_card_active")}
          <select id="set_card">${["uzcard", "humo", "tbc", "uzum"].map((c) => `<option value="${c}" ${st.card_active === c ? "selected" : ""}>${c}</option>`).join("")}</select>
        </label>
        <label>${wt("set_support_user")}<input type="text" id="set_supuser" value="${esc(st.support_username)}"></label>
        <label>${wt("set_sup_phone")}<input type="text" id="set_supphone" value="${esc(st.support_phone)}"></label>
        <label>${wt("set_sup_email")}<input type="text" id="set_supemail" value="${esc(st.support_email)}"></label>
        <label>${wt("set_admin_contact")}<input type="text" id="set_adminc" value="${esc(st.admin_username)}"></label>
      </div>
      <button class="mini-btn ok" style="width:100%;margin-top:10px" onclick="adminSaveSettings()">${wt("save")}</button>
    </div>
    <div class="admin-section">
      <div class="as-title">${wt("maintenance_lbl")}</div>
      ${FEATURE_ROWS.map((f) => `
      <div class="as-row" style="display:flex;justify-content:space-between;align-items:center;gap:8px">
        <span style="font-size:12px;color:var(--muted);flex:1">${wt(f.key)}</span>
        <button class="mini-btn ${st[f.key] ? "ok" : ""}" onclick="adminToggleFeature('${f.key}')">${st[f.key] ? wt("toggle_on") : wt("toggle_off")}</button>
      </div>`).join("")}
    </div>
    <div class="admin-section">
      <div class="as-title">${wt("admins_title")}</div>
      <div class="admin-search" style="margin-top:8px">
        <input type="text" id="adm-id-in" placeholder="${wt("admin_id_ph")}" inputmode="numeric">
        <button class="mini-btn ok" onclick="adminAddAdmin()">${wt("admin_add_btn")}</button>
      </div>
      <div id="adm-list">${renderAdminsList(adm)}</div>
    </div>`;
}

function renderAdminsList(adm) {
  const rows = [];
  const seen = new Set();
  for (const a of adm.admins || []) {
    seen.add(a.user_id);
    rows.push({ id: a.user_id, label: a.full_name || "", uname: a.username || "", removable: !a.is_base, base: a.is_base });
  }
  for (const id of adm.base_admins || []) {
    if (!seen.has(id)) rows.push({ id, label: "", uname: "", removable: false, base: true });
  }
  if (!rows.length) return `<div class="as-row">${wt("no_data")}</div>`;
  return rows.map((r) => `
    <div class="as-row" style="display:flex;justify-content:space-between;align-items:center;gap:8px">
      <span style="font-size:13px"><b>${esc(r.label || r.uname || "admin")}</b>${r.uname ? " @" + esc(r.uname) : ""} <span style="color:var(--muted)">#${r.id}</span>${r.base ? " · 🛡" : ""}</span>
      ${r.removable ? `<button class="mini-btn danger" onclick="adminRemoveAdmin(${r.id})">${wt("delete_btn")}</button>` : ""}
    </div>`).join("");
}

async function adminSaveSettings() {
  const num = (id) => (document.getElementById(id)?.value || "").trim();
  const settings = {
    keshbek_percent: num("set_keshbek"),
    referral_reward_topup_percent: num("set_ref"),
    star_rate_1000: num("set_star"),
    min_topup_card: num("set_min"),
    max_topup_card: num("set_max"),
    daily_bonus_amount: num("set_bonus"),
    pay_window_seconds: num("set_window"),
    card_active: document.getElementById("set_card")?.value || "uzcard",
    support_username: num("set_supuser"),
    support_phone: num("set_supphone"),
    support_email: num("set_supemail"),
    admin_username: num("set_adminc"),
  };
  const res = await api("/api/admin/settings_save", { settings });
  if (res.ok) {
    toast(wt("settings_saved"));
    haptic("success");
  } else {
    toast((res.field ? res.error + " (" + res.field + ")" : res.error) || wt("err_generic"));
    haptic("error");
  }
}

async function adminToggleMaintenance() {
  const res = await api("/api/admin/settings_save", { settings: { maintenance: !state.maintenance } });
  if (res.ok) {
    state.maintenance = !state.maintenance;
    toast(state.maintenance ? wt("toggle_on") : wt("toggle_off"));
    haptic("success");
    loadAdminSettings(document.getElementById("admin-content"));
  } else {
    toast(res.error || wt("err_generic"));
    haptic("error");
  }
}

async function adminAddAdmin() {
  const id = parseInt((document.getElementById("adm-id-in")?.value || "").trim(), 10);
  if (!id) return toast(wt("admin_no_user"));
  const res = await api("/api/admin/admin_add", { user_id: id });
  const msg = { exists: wt("admin_exists"), no_user: wt("admin_no_user") }[res.error];
  toast(res.ok ? wt("admin_added") : msg || res.error || wt("err_generic"));
  haptic(res.ok ? "success" : "error");
  if (res.ok) loadAdminSettings(document.getElementById("admin-content"));
}

async function adminRemoveAdmin(id) {
  const okc = await confirmDialog(wt("cf_admin_del", String(id)), "");
  if (!okc) return;
  const res = await api("/api/admin/admin_remove", { user_id: id });
  const msg = { self: wt("admin_self_err"), last: wt("admin_self_err"), base: wt("admin_self_err") }[res.error];
  toast(res.ok ? wt("admin_removed") : msg || res.error || wt("err_generic"));
  haptic(res.ok ? "success" : "error");
  if (res.ok) loadAdminSettings(document.getElementById("admin-content"));
}

/* Admin CSV export */
async function adminExport(type) {
  const res = await api("/api/admin/export", { type });
  if (!res.ok) return toast(wt("export_failed"));
  try {
    const blob = new Blob([res.csv], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = res.filename || type + ".csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
    haptic("success");
  } catch (e) {
    toast(wt("export_failed"));
  }
}

/* Admin audit */
async function loadAdminAudit(content) {
  content.innerHTML = `<div class="sk sk-card"></div><div class="sk sk-card"></div><div class="sk sk-card"></div>`;
  const res = await api("/api/admin/audit", { limit: 100 });
  if (!res.ok) return (content.innerHTML = emptyHtml("⚠️", wt("err_generic"), wt("err_load")));
  if (!res.audit || !res.audit.length) {
    content.innerHTML = emptyHtml("🕵️", wt("no_audit"), wt("admin_actions_here"));
    return;
  }
  content.innerHTML = res.audit.map((a, i) => `
    <div class="audit-item" style="animation-delay:${Math.min(i, 8) * 0.04}s">
      <div class="audit-action">${esc(a.action)}</div>
      <div class="audit-detail">${esc(a.detail || "—")}</div>
      <div class="audit-meta">
        <span>👤 ${a.admin_id}</span>
        <span>🕐 ${esc(a.created_at)}</span>
      </div>
    </div>`).join("");
}

function confirmDialog(title, text) {
  if (tg && tg.showPopup) {
    return new Promise((resolve) => {
      tg.showPopup({
        title: title || "",
        message: text || "",
        buttons: [
          { id: "yes", type: "default", text: wt("confirm") },
          { id: "no", type: "cancel", text: wt("cancel") },
        ],
      }, (id) => resolve(id === "yes"));
    });
  }
  const input = document.getElementById("modal-input");
  input.style.display = "none";
  document.getElementById("modal-title").textContent = title;
  document.getElementById("modal-text").textContent = text;
  document.getElementById("modal-overlay").classList.add("show");
  return new Promise((resolve) => {
    const okBtn = document.getElementById("modal-ok");
    const cancelBtn = document.getElementById("modal-cancel");
    const close = () => {
      document.getElementById("modal-overlay").classList.remove("show");
      okBtn.onclick = null;
      cancelBtn.onclick = null;
    };
    okBtn.onclick = () => { close(); resolve(true); };
    cancelBtn.onclick = () => { close(); resolve(false); };
  });
}

/* ---------------- INIT ---------------- */
async function init() {
  initTg();
  const _sl = document.getElementById("splash-lottie");
  if (_sl && playLottie(_sl, "loading")) _sl.textContent = "";
  skeletonGames(6);
  const res = await api("/api/init");
  if (!res.ok) {
    if (res.error === "banned") {
      hideSplash();
      document.getElementById("games-grid").innerHTML =
        emptyHtml("🚫", wt("banned_label"), res.message || wt("banned_text"));
      return;
    }
    hideSplash();
    document.getElementById("games-grid").innerHTML =
      emptyHtml("🔒", wt("open_in_tg_title"), wt("open_in_tg"));
    return;
  }
  if (res.i18n) setWebappI18n(res.user?.lang || "uz", res.i18n);
  hydrateI18n();
  state.user = res.user;
  state.isAdmin = !!res.is_admin;
  state.maintenance = !!res.maintenance;
  state.games = res.games;
  state.card_number = res.card_number;
  state.card_uzcard = (res.cards && res.cards.uzcard) || res.card_number || "";
  state.card_humo = (res.cards && res.cards.humo) || "";
  state.card_tbc = (res.cards && res.cards.tbc) || "";
  state.card_uzum = (res.cards && res.cards.uzum) || "";
  state.cardsList = Array.isArray(res.cards_list) ? res.cards_list : [];
  state.card_name = res.card_name;
  state.inviteLink = res.invite_link || "";
  state.botUsername = res.bot_username || "";
  state.adminUsername = res.admin_username || "";
  state.supportUsername = (res.support || "").replace(/^@/, "") || res.bot_username || "";
  state.supportPhone = res.support_phone || "";
  state.supportEmail = res.support_email || "";
  state.payWindowSecs = res.pay_window_seconds || 300;
  state.minTopup = res.min_topup || 3000;
  if (res.daily_bonus) state.dailyBonus = res.daily_bonus;
  const modeInit = localStorage.getItem("gs_theme_mode");
  applyTheme(modeInit || res.theme || localStorage.getItem("gs_theme") || "auto", false);
  if (res.favorites) state.favorites = res.favorites;
  if (typeof res.unread_notifs === "number") { state.unreadNotifs = res.unread_notifs; updateNotifBadge(); }
  loadCartCloud((arr) => { state.cart = arr; updateCartBadge(); });

  hideSplash();
  document.getElementById("nav-admin").style.display = state.isAdmin ? "flex" : "none";
  moveNavGlow("view-home");
  renderUser();
  renderBonus();
  renderHome();
  renderGameFilterBar();
  if (state.maintenance) {
    const grid = document.getElementById("games-grid");
    if (grid && grid.parentElement && !document.getElementById("maint-banner")) {
      const b = document.createElement("div");
      b.id = "maint-banner";
      b.style.cssText = "margin:4px 14px 10px;padding:10px 14px;background:rgba(255,170,0,.12);border:1px solid rgba(255,170,0,.35);border-radius:14px;font-size:13px;color:#ffcc66;text-align:center";
      b.textContent = wt("maintenance_banner");
      grid.parentElement.insertBefore(b, grid);
    }
  }
}

window.addEventListener("resize", () => {
  const active = document.querySelector(".nav-item.active");
  if (active) moveNavGlow(active.dataset.view);
});

document.addEventListener("DOMContentLoaded", init);
