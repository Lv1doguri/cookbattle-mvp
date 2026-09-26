/* 요리왕 웹앱 — 백엔드(FastAPI)가 같은 주소에서 제공. 빌드 도구 없이 동작하는 순수 JS. */
"use strict";

// ================= 공통 유틸 =================
const $app = document.getElementById("app");
const $tab = document.getElementById("tabbar");
const $ = (id) => document.getElementById(id);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const won = (n) => (n == null ? "-" : "₩" + Number(n).toLocaleString("ko-KR"));
const num = (n) => Number(n || 0).toLocaleString("ko-KR");
const initial = (name) => esc((name || "?").trim().charAt(0));
const FOOD_ICON = { rice: "🍚", noodle: "🍜", pasta: "🍝", meat: "🥩", soup: "🍲", side: "🥚", healthy: "🥗", dessert: "🍠" };
const FOOD_BG = { rice: "#E8D6CE,#D9BBAC", noodle: "#E1E6D4,#C6D2AE", pasta: "#F4EDE2,#E6D6BD", meat: "#F0D9D2,#DDB3A6",
  soup: "#F1E3C8,#E0C592", side: "#EFE7C6,#DFCB92", healthy: "#DDEBD3,#BCD7A8", dessert: "#EEDDE6,#D9B9CB" };
const stars = (n) => { const r = Math.round(n || 0); return "★".repeat(r) + "☆".repeat(5 - r); };
const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

function toast(msg, ms = 2600) {
  const t = document.getElementById("toast");
  t.textContent = msg; t.hidden = false;
  clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), ms);
}

function foodThumb(r, size = 92) {
  const bg = FOOD_BG[r.food_type] || "#E9ECE1,#D5DCC9";
  const inner = r.image_url ? `<img src="${esc(r.image_url)}" alt="" loading="lazy">` : (FOOD_ICON[r.food_type] || "🍳");
  return `<div class="food" style="width:${size}px;height:${size}px;background:linear-gradient(135deg,${bg})">${inner}</div>`;
}

const icons = {
  back: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/></svg>',
  filter: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h10M18 7h2M4 17h2M10 17h10"/><circle cx="16" cy="7" r="2"/><circle cx="8" cy="17" r="2"/></svg>',
  search: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="6"/><path d="M20 20l-4.5-4.5"/></svg>',
  clock: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/></svg>',
  bm: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linejoin="round"><path d="M7 4h10v16l-5-4-5 4z"/></svg>',
  bmOn: '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2.2" stroke-linejoin="round"><path d="M7 4h10v16l-5-4-5 4z"/></svg>',
  recipe: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 10h16v6a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4z"/><path d="M2 10h20"/><path d="M9 6c0-1 1-1 1-2M14 6c0-1 1-1 1-2"/></svg>',
  battle: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 4h8v5a4 4 0 0 1-8 0z"/><path d="M8 6H5a3 3 0 0 0 3 4M16 6h3a3 3 0 0 1-3 4"/><path d="M12 13v4M8 20h8"/></svg>',
  home: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 11l8-7 8 7v8a1 1 0 0 1-1 1h-4v-6h-6v6H5a1 1 0 0 1-1-1z"/></svg>',
  shop: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="9" width="16" height="11" rx="2"/><path d="M3 9h18M12 9v11M12 9c-2 0-4-1-4-3s3-2 4 3c1-5 4-5 4-3s-2 3-4 3"/></svg>',
  menu: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M5 7h14M5 12h14M5 17h14"/></svg>',
  chev: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6"/></svg>',
};

// ================= API =================
const store = {
  get token() { return localStorage.getItem("cb_token"); },
  set token(v) { v ? localStorage.setItem("cb_token", v) : localStorage.removeItem("cb_token"); },
  user: null,
  meta: null,
  recipeOptions: null,
};

class ApiError extends Error { constructor(status, detail) { super(detail); this.status = status; } }

async function api(method, path, body, { silent = false } = {}) {
  const headers = {};
  if (store.token) headers.Authorization = "Bearer " + store.token;
  let payload;
  if (body instanceof FormData) payload = body;
  else if (body !== undefined) { headers["Content-Type"] = "application/json"; payload = JSON.stringify(body); }
  let res;
  try {
    res = await fetch(path, { method, headers, body: payload });
  } catch (e) {
    showOffline();
    throw new ApiError(0, "서버에 연결할 수 없어요");
  }
  let data = null;
  const text = await res.text();
  try { data = text ? JSON.parse(text) : null; } catch { data = { detail: text }; }
  if (res.status === 401 && path !== "/auth/login") {
    store.token = null; store.user = null;
    if (!location.hash.startsWith("#/login") && !location.hash.startsWith("#/signup")) {
      toast("다시 로그인해 주세요"); go("/login");
    }
    throw new ApiError(401, data?.detail || "로그인이 필요해요");
  }
  if (!res.ok) {
    const msg = typeof data?.detail === "string" ? data.detail : "요청을 처리하지 못했어요";
    if (!silent) toast(msg);
    throw new ApiError(res.status, msg);
  }
  return data;
}
const GET = (p, o) => api("GET", p, undefined, o);
const POST = (p, b, o) => api("POST", p, b, o);
const PATCH = (p, b, o) => api("PATCH", p, b, o);
const DEL = (p, o) => api("DELETE", p, undefined, o);
const qs = (obj) => {
  const p = new URLSearchParams();
  Object.entries(obj).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "") p.set(k, v); });
  const s = p.toString(); return s ? "?" + s : "";
};

async function refreshMe() { store.user = await GET("/users/me"); return store.user; }

function showOffline() {
  $tab.hidden = true;
  $app.className = "no-tab";
  $app.innerHTML = `<div class="pad" style="padding-top:120px"><div class="empty"><div class="ic">📡</div>
    <h2 class="ttl-s" style="text-align:center">연결을 확인해 주세요</h2>
    <p>서버에 연결할 수 없어요.<br>백엔드가 켜져 있는지 확인해 주세요.</p>
    <button class="btn mt16" data-act="retry">다시 시도</button></div></div>`;
}

// ================= 라우터 =================
const routes = [];
const route = (pattern, render, opts = {}) => {
  const keys = []; const re = new RegExp("^" + pattern.replace(/:(\w+)/g, (_, k) => (keys.push(k), "([^/]+)")) + "$");
  routes.push({ re, keys, render, opts });
};
const go = (path) => { if (location.hash === "#" + path) render(); else location.hash = path; };
const back = () => (history.length > 1 ? history.back() : go("/recipes"));
let renderSeq = 0;

async function render() {
  const [path, query = ""] = (location.hash.slice(1) || "/recipes").split("?");
  const params = Object.fromEntries(new URLSearchParams(query));
  const r = routes.find((x) => x.re.test(path));
  if (!r) return go("/recipes");
  const m = path.match(r.re); r.keys.forEach((k, i) => (params[k] = decodeURIComponent(m[i + 1])));
  if (!r.opts.public && !store.token) return go("/login");
  if (!r.opts.public && !store.user) { try { await refreshMe(); } catch { return; } }
  const seq = ++renderSeq;
  $app.className = r.opts.tab ? "" : "no-tab";
  renderTabbar(r.opts.tab);
  $app.innerHTML = `<div class="loading"><div class="spin"></div></div>`;
  window.scrollTo(0, 0);
  try {
    const html = await r.render(params);
    if (seq !== renderSeq) return; // 그 사이에 다른 화면으로 이동함
    if (typeof html === "string") $app.innerHTML = html;
    r.render.after && r.render.after(params);
  } catch (e) {
    if (seq !== renderSeq || e.status === 401 || e.status === 0) return;
    $app.innerHTML = `<div class="empty" style="padding-top:120px"><div class="ic">😥</div><p>${esc(e.message)}</p>
      <button class="btn ghost sm" data-act="back">돌아가기</button></div>`;
  }
}
window.addEventListener("hashchange", render);

function renderTabbar(active) {
  if (!active) { $tab.hidden = true; return; }
  const tabs = [["recipes", "레시피", icons.recipe], ["battle", "대결", icons.battle], ["home", "홈", icons.home], ["shop", "상점", icons.shop], ["menu", "메뉴", icons.menu]];
  $tab.innerHTML = tabs.map(([k, l, ic]) => `<a href="#/${k}" class="${k === active ? "on" : ""}">${ic}${l}</a>`).join("");
  $tab.hidden = false;
}

// 화면 공통 헤더
const header = (title, { backBtn = true, right = "", small = true } = {}) => `
  <div class="hdr"><div class="top">
    ${backBtn ? `<button class="ibtn" data-act="back" aria-label="뒤로">${icons.back}</button>` : ""}
    <h1 class="${small ? "ttl-s" : "ttl"}">${esc(title)}</h1>${right}
  </div></div>`;

// 클릭 위임: data-act="이름" → actions[이름](el, event)
const actions = {
  back: () => back(),
  retry: () => render(),
  go: (el) => go(el.dataset.to),
};
document.addEventListener("click", (e) => {
  const el = e.target.closest("[data-act]");
  if (!el || el.disabled) return;
  const fn = actions[el.dataset.act];
  if (fn) { e.preventDefault(); fn(el, e); }
});

// 버튼 잠그고 실행 (중복 클릭 방지)
async function busy(btn, fn) {
  if (btn) { btn.disabled = true; btn._t = btn.textContent; }
  try { return await fn(); } finally { if (btn) { btn.disabled = false; } }
}

// ================= 로그인 / 가입 / 튜토리얼 =================
route("/login", async () => `
  <div class="pad" style="padding-top:90px">
    <div class="logo">🍳</div>
    <h1 class="ttl center" style="font-size:34px">요리왕</h1>
    <p class="center muted">요리하고, 공유하고, 대결하다</p>
    <form id="loginForm" class="stack mt24">
      <div class="field"><label for="le">이메일</label><input id="le" class="input" type="email" autocomplete="email" required></div>
      <div class="field"><label for="lp">비밀번호</label><input id="lp" class="input" type="password" autocomplete="current-password" required></div>
      <button class="btn mt12" type="submit">로그인</button>
    </form>
    <p class="center muted mt16">계정이 없으신가요? <a href="#/signup" class="b">회원가입</a></p>
  </div>`, { public: true });
routes.at(-1).render.after = () => {
  document.getElementById("loginForm").onsubmit = async (e) => {
    e.preventDefault();
    const btn = e.submitter;
    await busy(btn, async () => {
      const d = await POST("/auth/login", { email: $("le").value.trim(), password: $("lp").value });
      store.token = d.access_token; store.user = d.user;
      go(d.user.tutorial_completed ? "/battle" : "/onboarding");
    }).catch(() => {});
  };
};

route("/signup", async () => {
  store.meta = store.meta || (await GET("/meta"));
  const skills = store.meta.skills;
  return `${header("회원가입")}
  <div class="pad">
    <h2 class="ttl" style="font-size:26px">반가워요!</h2><p class="muted">요리왕에서 쓸 이름을 알려주세요</p>
    <form id="signupForm" class="stack mt16">
      <div class="field"><label for="se">이메일</label><input id="se" class="input" type="email" autocomplete="email" required></div>
      <div class="field"><label for="sn">닉네임</label>
        <div class="row"><input id="sn" class="input" maxlength="12" required placeholder="2~12자 한글·영문·숫자">
        <button type="button" class="btn ghost sm" data-act="checkNick" style="height:52px">중복 확인</button></div>
        <span id="snHint" class="hint"></span></div>
      <div class="field"><label for="sp">비밀번호</label><input id="sp" class="input" type="password" autocomplete="new-password" required minlength="8" placeholder="8자 이상, 영문+숫자"></div>
      <div class="field"><label for="si">초대 코드 (선택)</label><input id="si" class="input" maxlength="16" placeholder="친구에게 받은 코드"></div>
      <h3 class="sec mt12">요리 실력이 어느 정도인가요?</h3>
      <div class="stack" id="skills">${Object.entries(skills).map(([k, s]) => `
        <button type="button" class="skill" data-act="pickSkill" data-skill="${k}">
          <span class="lv">${esc(s.label)}</span><span><b>${esc(s.label)}급</b><br><span class="small muted">${esc(s.description)}</span></span>
        </button>`).join("")}</div>
      <p class="hint">요리 실력은 대결 그룹이 되고, 가입 후에는 바꿀 수 없어요</p>
      <button class="btn mt8" type="submit">가입하기</button>
    </form>
  </div>`;
});
routes.at(-1).opts.public = true;
routes.at(-1).render.after = () => {
  let skill = null;
  actions.pickSkill = (el) => { skill = el.dataset.skill; document.querySelectorAll(".skill").forEach((b) => b.classList.toggle("on", b === el)); };
  actions.checkNick = async () => {
    const h = $("snHint"); const v = $("sn").value.trim();
    if (!v) return;
    const r = await GET("/auth/check-nickname" + qs({ nickname: v }));
    h.textContent = r.available ? "사용할 수 있는 닉네임이에요" : r.reason; h.className = "hint " + (r.available ? "ok" : "err");
  };
  $("sn").addEventListener("blur", () => actions.checkNick());
  document.getElementById("signupForm").onsubmit = async (e) => {
    e.preventDefault();
    if (!skill) return toast("요리 실력을 선택해 주세요");
    await busy(e.submitter, async () => {
      const d = await POST("/auth/signup", { email: $("se").value.trim(), nickname: $("sn").value.trim(), password: $("sp").value,
        skill, invite_code: $("si").value.trim() || null });
      store.token = d.access_token; store.user = d.user; go("/onboarding");
    }).catch(() => {});
  };
};

const TUTORIAL = [
  ["🧭", "하단 탭으로 이동해요", "레시피 · 대결 · 홈 · 상점 · 메뉴를 오갈 수 있어요."],
  ["🏆", "매일 요리 대결", "하루 요리해서 사진을 올리고, 다음 하루는 참가자끼리 투표해요. 참가만 해도 +10P!"],
  ["📷", "여러 구도로 인증", "완성샷·키워드 인증샷과 랜덤 구도 1장을 찍어요. 같은 사진은 올릴 수 없어요."],
  ["🎁", "포인트로 기프티콘", "순위 포인트로 레벨을 올리고, 상점에서 기프티콘으로 바꿔요."],
];
route("/onboarding", async () => {
  const step = Math.min(store.user.tutorial_step || 0, TUTORIAL.length - 1);
  const [ic, t, d] = TUTORIAL[step];
  return `<div class="pad" style="padding-top:24px">
    <div class="between"><span class="badge">${step + 1} / ${TUTORIAL.length}</span><button class="btn ghost sm" data-act="tutSkip">건너뛰기</button></div>
    <div class="empty" style="padding-top:90px"><div class="ic" style="font-size:80px">${ic}</div>
      <h2 class="ttl" style="text-align:center">${esc(t)}</h2><p style="font-size:16px;line-height:1.6">${esc(d)}</p></div>
    <button class="btn mt24" data-act="tutNext">${step + 1 < TUTORIAL.length ? "다음" : "시작하기"}</button></div>`;
});
actions.tutNext = async () => {
  const next = (store.user.tutorial_step || 0) + 1;
  store.user = next >= TUTORIAL.length ? await PATCH("/users/me/tutorial", { completed: true, step: TUTORIAL.length })
    : await PATCH("/users/me/tutorial", { step: next });
  store.user.tutorial_completed ? go("/battle") : render();
};
actions.tutSkip = async () => { store.user = await PATCH("/users/me/tutorial", { completed: true }); go("/battle"); };

// ================= 레시피 =================
const RF_KEY = "cb_recipe_filter";
const rf = Object.assign({ q: "", have: "", type: [], difficulty: [], tag: [], budget: null, time: null, sort: "latest", quick: 0 },
  JSON.parse(sessionStorage.getItem(RF_KEY) || "{}"));
const saveRf = () => sessionStorage.setItem(RF_KEY, JSON.stringify(rf));

async function recipeOptions() { return (store.recipeOptions = store.recipeOptions || (await GET("/recipes/options"))); }

function recipeQuery(opts, extra = {}) {
  const p = { q: rf.q, have: rf.have, type: rf.type.join(","), difficulty: rf.difficulty.join(","), tag: rf.tag.join(","), sort: rf.sort };
  if (rf.budget != null) Object.assign(p, opts.budgets[rf.budget].params);
  if (rf.time != null) Object.assign(p, opts.times[rf.time].params);
  // 빠른 칩은 필터 화면 조건 위에 덧붙인다 (같은 키면 합침)
  const quick = opts.quick_filters[rf.quick]?.params || {};
  for (const [k, v] of Object.entries(quick)) {
    if ((k === "tag" || k === "difficulty") && p[k]) { if (!p[k].split(",").includes(v)) p[k] += "," + v; } else p[k] = v;
  }
  return qs({ ...p, ...extra });
}
const filterCount = () => rf.type.length + rf.difficulty.length + rf.tag.length + (rf.budget != null) + (rf.time != null) + (rf.have ? 1 : 0);

function recipeCard(r) {
  const extra = r.missing_ingredients
    ? `<span class="small" style="color:${r.missing_ingredients.length ? "#8A5A12" : "var(--g1)"}">${r.missing_ingredients.length
      ? "더 필요: " + esc(r.missing_ingredients.slice(0, 3).join(", ")) + (r.missing_ingredients.length > 3 ? " 외" : "") : "지금 재료로 만들 수 있어요!"}</span>` : "";
  return `<div class="card"><div class="rc" data-act="go" data-to="/recipe/${r.id}">
    ${foodThumb(r)}
    <div style="flex-grow:1;display:flex;flex-direction:column;gap:5px;min-width:0">
      ${r.badge ? `<span class="badge ${r.source === "winner" ? "gold" : ""}" style="align-self:flex-start">${esc(r.badge)}</span>` : ""}
      <span style="font-size:16px;font-weight:800">${esc(r.title)}</span>
      <span class="meta">${icons.clock}${r.cook_minutes ? r.cook_minutes + "분" : "-"} · ${won(r.estimated_cost)}</span>
      <span class="small muted">${esc(r.difficulty_label || "")}${r.difficulty_label ? " · " : ""}저장 ${r.save_count}</span>${extra}
    </div>
    <button class="bm ${r.saved_by_me ? "on" : ""}" data-act="toggleSave" data-id="${r.id}" data-saved="${r.saved_by_me ? 1 : 0}" aria-label="저장">${r.saved_by_me ? icons.bmOn : icons.bm}</button>
  </div></div>`;
}

actions.toggleSave = async (el, e) => {
  e.stopPropagation();
  const saved = el.dataset.saved === "1";
  const r = saved ? await DEL(`/recipes/${el.dataset.id}/save`) : await POST(`/recipes/${el.dataset.id}/save`);
  el.dataset.saved = r.saved_by_me ? "1" : "0"; el.classList.toggle("on", r.saved_by_me);
  el.innerHTML = r.saved_by_me ? icons.bmOn : icons.bm;
  toast(r.saved_by_me ? "저장했어요" : "저장을 취소했어요", 1400);
};

let recipePage = { offset: 0, total: 0 };
route("/recipes", async () => {
  const opts = await recipeOptions();
  const fc = filterCount();
  return `<div class="hdr">
    <div class="top"><h1 class="ttl">레시피</h1>
      <button class="ibtn" data-act="go" data-to="/filter" aria-label="필터" style="position:relative">${icons.filter}
        ${fc ? `<span class="badge gold" style="position:absolute;top:2px;right:0;height:18px;padding:0 6px">${fc}</span>` : ""}</button></div>
    <label class="search">${icons.search}<input id="rq" aria-label="검색" placeholder="재료, 요리 이름, 키워드 검색" value="${esc(rf.q)}"></label>
    <div class="chips">${opts.quick_filters.map((c, i) => `<button class="chip ${rf.quick === i ? "on" : ""}" data-act="quick" data-i="${i}">${esc(c.label)}</button>`).join("")}</div>
  </div>
  <div class="between" style="padding:6px 22px 10px;font-size:13px">
    <span class="b" style="color:#4A5343" id="rcount">…</span>
    <select id="rsort" aria-label="정렬" style="border:0;background:none;font-weight:800;color:var(--g2)">
      ${opts.sorts.map((s) => `<option value="${s.key}" ${rf.sort === s.key ? "selected" : ""}>${esc(s.label)}</option>`).join("")}</select>
  </div>
  ${rf.have ? `<div class="pad" style="margin-bottom:10px"><div class="banner info">🧊 재료로 찾기: ${esc(rf.have)} <button class="btn ghost sm" style="margin-left:auto;height:30px" data-act="clearHave">해제</button></div></div>` : ""}
  <div class="pad stack" id="rlist"></div>
  <div class="pad mt12" id="rmore"></div>
  <button class="fab" data-act="go" data-to="/recipe-new">＋ 레시피 올리기</button>`;
}, { tab: "recipes" });
routes.at(-1).render.after = () => {
  loadRecipes(true);
  document.getElementById("rq").addEventListener("input", debounce((e) => { rf.q = e.target.value.trim(); saveRf(); loadRecipes(true); }, 300));
  document.getElementById("rsort").onchange = (e) => { rf.sort = e.target.value; saveRf(); loadRecipes(true); };
};
async function loadRecipes(reset) {
  const opts = await recipeOptions();
  if (reset) recipePage = { offset: 0, total: 0 };
  const list = document.getElementById("rlist"); if (!list) return;
  const d = await GET("/recipes" + recipeQuery(opts, { limit: 20, offset: recipePage.offset }));
  if (!document.getElementById("rlist")) return;
  recipePage.total = d.total; recipePage.offset += d.items.length;
  document.getElementById("rcount").textContent = `${d.total}개 결과`;
  const html = d.items.map(recipeCard).join("");
  if (reset) list.innerHTML = html || `<div class="empty"><div class="ic">🍽️</div>조건에 맞는 레시피가 없어요<br><span class="small">필터를 줄여 보거나 직접 올려 보세요</span></div>`;
  else list.insertAdjacentHTML("beforeend", html);
  document.getElementById("rmore").innerHTML = recipePage.offset < recipePage.total ? `<button class="btn ghost" data-act="moreRecipes">더 보기</button>` : "";
}
actions.moreRecipes = () => loadRecipes(false);
actions.quick = (el) => { rf.quick = +el.dataset.i; saveRf(); document.querySelectorAll(".chips .chip").forEach((c) => c.classList.toggle("on", c === el)); loadRecipes(true); };
actions.clearHave = () => { rf.have = ""; saveRf(); render(); };

// ---- 필터 (05) ----
route("/filter", async () => {
  const o = await recipeOptions();
  const chip = (group, key, label, on) => `<button class="chip ${on ? "on" : ""}" data-act="fchip" data-g="${group}" data-k="${esc(key)}">${on ? "✓ " : ""}${esc(label)}</button>`;
  return `${header("필터", { right: `<button class="btn ghost sm" data-act="fReset">초기화</button>` })}
  <div class="pad stack">
    <div class="card p"><h2 class="sec">🧊 재료로 찾기</h2><p class="small muted" style="margin-top:-6px">냉장고 속 재료로 만들 수 있는 요리를 찾아요</p>
      <input id="fhave" class="input" placeholder="예: 계란, 김치, 밥" value="${esc(rf.have)}"></div>
    <div class="card p stack" style="gap:18px">
      <div><h2 class="sec">종류</h2><div class="wrap">${o.food_types.map((t) => chip("type", t.key, t.label, rf.type.includes(t.key))).join("")}</div></div>
      <div><h2 class="sec">예산</h2><div class="wrap">${o.budgets.map((b, i) => chip("budget", i, b.label, rf.budget === i)).join("")}</div></div>
      <div><h2 class="sec">조리 시간</h2><div class="wrap">${o.times.map((b, i) => chip("time", i, b.label, rf.time === i)).join("")}</div></div>
      <div><h2 class="sec">난이도</h2><div class="wrap">${o.difficulties.map((d) => chip("difficulty", d.key, d.label, rf.difficulty.includes(d.key))).join("")}</div></div>
      <div><h2 class="sec">태그</h2><div class="wrap">${o.tags.map((t) => chip("tag", t, t, rf.tag.includes(t))).join("")}</div></div>
    </div>
    <div style="height:90px"></div>
  </div>
  <div class="sticky-bottom"><button class="btn" data-act="fApply" id="fbtn">레시피 보기</button></div>`;
});
routes.at(-1).render.after = () => {
  const upd = debounce(updateFilterCount, 250);
  document.getElementById("fhave").addEventListener("input", (e) => { rf.have = e.target.value.split(/[,\s]+/).filter(Boolean).join(","); saveRf(); upd(); });
  updateFilterCount();
};
async function updateFilterCount() {
  const o = await recipeOptions();
  const d = await GET("/recipes/count" + recipeQuery(o), { silent: true }).catch(() => null);
  const b = document.getElementById("fbtn"); if (b && d) b.textContent = `레시피 ${d.total}개 보기`;
}
actions.fchip = (el) => {
  const g = el.dataset.g, k = el.dataset.k;
  if (g === "budget" || g === "time") rf[g] = rf[g] === +k ? null : +k;
  else rf[g] = rf[g].includes(k) ? rf[g].filter((x) => x !== k) : [...rf[g], k];
  saveRf(); render();
};
actions.fReset = () => { Object.assign(rf, { have: "", type: [], difficulty: [], tag: [], budget: null, time: null, quick: 0 }); saveRf(); render(); };
actions.fApply = () => { rf.quick = 0; saveRf(); go("/recipes"); };

// ---- 상세 ----
route("/recipe/:id", async ({ id }) => {
  const [r, reviews] = await Promise.all([GET(`/recipes/${id}`), GET(`/recipes/${id}/reviews`)]);
  const bg = FOOD_BG[r.food_type] || "#E9ECE1,#D5DCC9";
  return `<div style="position:relative;height:300px;background:linear-gradient(135deg,${bg});display:flex;align-items:center;justify-content:center;font-size:90px;overflow:hidden">
      ${r.image_url ? `<img src="${esc(r.image_url)}" alt="${esc(r.title)} 사진" style="width:100%;height:100%;object-fit:cover">` : FOOD_ICON[r.food_type] || "🍳"}
      <div class="between" style="position:absolute;top:16px;left:12px;right:12px">
        <button class="ibtn" style="background:#fff" data-act="back" aria-label="뒤로">${icons.back}</button>
        <button class="bm ${r.saved_by_me ? "on" : ""}" style="align-self:auto" data-act="toggleSave" data-id="${r.id}" data-saved="${r.saved_by_me ? 1 : 0}" aria-label="저장">${r.saved_by_me ? icons.bmOn : icons.bm}</button>
      </div></div>
    <div class="pad stack" style="margin-top:-24px;position:relative">
      <div class="card p stack">
        <div class="row small"><span class="av sm">${initial(r.author_nickname)}</span><span class="b">${esc(r.author_nickname || "익명")}</span>
          ${r.badge ? `<span class="badge ${r.source === "winner" ? "gold" : ""}">${esc(r.badge)}</span>` : ""}</div>
        <h1 style="margin:4px 0 0;font-size:26px;letter-spacing:-.8px">${esc(r.title)}</h1>
        ${r.description ? `<p class="muted" style="margin:0">${esc(r.description)}</p>` : ""}
        <div class="wrap">${r.tags.map((t) => `<span class="badge">#${esc(t)}</span>`).join("")}${r.food_type_label ? `<span class="badge blue">${esc(r.food_type_label)}</span>` : ""}</div>
        <div class="row" style="align-items:stretch">
          <div class="stat"><span>예상 재료비</span><b>${r.estimated_cost != null ? "약 " + num(r.estimated_cost) + "원" : "-"}</b></div>
          <div class="stat"><span>조리 시간</span><b>${r.cook_minutes ? r.cook_minutes + "분" : "-"}</b></div>
          <div class="stat"><span>난이도</span><b>${esc(r.difficulty_label || "-")}</b></div>
        </div>
      </div>
      <div class="card p"><h2 class="sec">재료</h2>${r.ingredients.map((i) => `<div class="ing"><span>${esc(i.name)}</span><span class="muted">${esc(i.amount || "")}${i.price != null ? ` · ${num(i.price)}원` : ""}</span></div>`).join("")}
        ${r.tools ? `<p class="small muted mt8">🍳 도구: ${esc(r.tools)}</p>` : ""}</div>
      <div class="card p"><h2 class="sec">조리 과정</h2>${r.steps.map((s, i) => `<div class="step"><span class="num">${i + 1}</span><span>${esc(s)}</span></div>`).join("")}</div>
      ${r.is_mine ? `<div class="row"><button class="btn ghost" data-act="go" data-to="/recipe/${r.id}/edit">수정</button><button class="btn danger" data-act="delRecipe" data-id="${r.id}">삭제</button></div>`
        : r.completed_by_me ? `<div class="banner info">✅ 따라하기 완료! (+1P 받았어요)</div>`
        : `<label class="btn ghost">📷 따라 만들었어요 (사진 인증 +1P)<input type="file" accept="image/*" class="visually-hidden" id="doneFile" data-id="${r.id}"></label>`}
      <div class="card p"><h2 class="sec">후기 ${reviews.length}</h2>
        ${reviews.map((v) => `<div class="lr"><span class="av sm">${initial(v.nickname)}</span><div style="flex:1"><b class="small">${esc(v.nickname)}</b><div style="font-size:14px">${esc(v.content)}</div></div>
          ${v.is_mine ? `<button class="x" data-act="delReview" data-id="${v.id}" aria-label="삭제">✕</button>` : ""}</div>`).join("") || `<p class="small muted">첫 후기를 남겨 주세요</p>`}
      </div>
      <div style="height:70px"></div>
    </div>
    <form class="sticky-bottom row" id="reviewForm"><input class="input" id="rvText" maxlength="500" placeholder="댓글을 입력하세요" aria-label="댓글"><button class="btn sm" style="height:52px">등록</button></form>`;
});
routes.at(-1).render.after = ({ id }) => {
  document.getElementById("reviewForm").onsubmit = async (e) => {
    e.preventDefault(); const t = document.getElementById("rvText").value.trim(); if (!t) return;
    await busy(e.submitter, () => POST(`/recipes/${id}/reviews`, { content: t })).then(() => render()).catch(() => {});
  };
  const f = document.getElementById("doneFile");
  if (f) f.onchange = async () => {
    if (!f.files[0]) return; const fd = new FormData(); fd.append("file", f.files[0]);
    await POST(`/recipes/${id}/complete`, fd).then(() => { toast("따라하기 완료! +1P"); render(); }).catch(() => {});
  };
};
actions.delReview = async (el) => { if (!confirm("후기를 삭제할까요?")) return; await DEL(`/reviews/${el.dataset.id}`); render(); };
actions.delRecipe = async (el) => { if (!confirm("레시피를 삭제할까요? 저장·후기도 함께 지워져요")) return; await DEL(`/recipes/${el.dataset.id}`); toast("삭제했어요"); go("/recipes"); };

// ---- 레시피 올리기 / 수정 / 우승 레시피 공유 ----
function recipeForm(o, r, title) {
  const ings = r?.ingredients?.length ? r.ingredients : [{ name: "", amount: "", price: null }, { name: "", amount: "", price: null }];
  const steps = r?.steps?.length ? r.steps : ["", ""];
  const one = (g, key, label, on) => `<button type="button" class="chip ${on ? "on" : ""}" data-act="formChip" data-g="${g}" data-k="${esc(key)}">${esc(label)}</button>`;
  return `${header(title)}
  <form id="recipeForm" class="pad stack">
    <div class="card p stack">
      <div class="field"><label>요리 사진</label>
        <label class="slot" style="padding:0;cursor:pointer"><span class="pv" id="rimgPv">${r?.image_url ? `<img src="${esc(r.image_url)}" alt="">` : "＋"}</span>
        <span class="small muted">완성된 요리 사진 1장<br>(위치정보는 자동으로 지워져요)</span>
        <input type="file" accept="image/*" id="rimg" class="visually-hidden"></label></div>
      <div class="field"><label for="rt">요리 이름 *</label><input id="rt" class="input" maxlength="50" required value="${esc(r?.title)}"></div>
      <div class="field"><label for="rd">한 줄 소개</label><textarea id="rd" class="input" maxlength="1000">${esc(r?.description)}</textarea></div>
    </div>
    <div class="card p stack">
      <div><h2 class="sec">종류 *</h2><div class="wrap" data-single="food_type">${o.food_types.map((t) => one("food_type", t.key, t.label, r?.food_type === t.key)).join("")}</div></div>
      <div><h2 class="sec">난이도 *</h2><div class="wrap" data-single="difficulty">${o.difficulties.map((d) => one("difficulty", d.key, d.label, r?.difficulty === d.key)).join("")}</div></div>
      <div class="field"><label for="rm">조리 시간 (분) *</label><input id="rm" class="input" type="number" min="1" max="600" required value="${esc(r?.cook_minutes || "")}"></div>
      <div><h2 class="sec">태그</h2><div class="wrap">${o.tags.map((t) => one("tags", t, t, r?.tags?.includes(t))).join("")}</div></div>
    </div>
    <div class="card p stack"><div class="between"><h2 class="sec" style="margin:0">재료 *</h2><span class="small muted">가격을 적으면 재료비가 자동 계산돼요</span></div>
      <div class="ingrow small muted"><span>재료</span><span>분량</span><span>가격(원)</span><span></span></div>
      <div id="ings" class="stack">${ings.map(ingRow).join("")}</div>
      <button type="button" class="btn ghost sm" data-act="addIng">＋ 재료 추가</button>
      <div class="between"><span class="b">예상 재료비</span><span class="b" id="costSum">-</span></div></div>
    <div class="card p stack"><h2 class="sec" style="margin:0">조리 과정 *</h2><div id="steps" class="stack">${steps.map(stepRow).join("")}</div>
      <button type="button" class="btn ghost sm" data-act="addStep">＋ 단계 추가</button>
      <div class="field"><label for="rtools">사용 도구</label><input id="rtools" class="input" maxlength="100" placeholder="예: 전자레인지, 프라이팬" value="${esc(r?.tools)}"></div></div>
    <div style="height:80px"></div>
    <div class="sticky-bottom"><button class="btn" type="submit">${r?.id ? "수정 완료" : "레시피 올리기"}</button></div>
  </form>`;
}
const ingRow = (i) => `<div class="ingrow"><input class="input" data-f="name" placeholder="김치" maxlength="30" value="${esc(i.name)}">
  <input class="input" data-f="amount" placeholder="1컵" maxlength="20" value="${esc(i.amount)}">
  <input class="input" data-f="price" type="number" min="0" placeholder="1500" value="${i.price ?? ""}"><button type="button" class="x" data-act="rmRow" aria-label="삭제">✕</button></div>`;
const stepRow = (s, i) => `<div class="row"><span class="num">${(i ?? 0) + 1}</span><input class="input" data-f="step" maxlength="300" placeholder="예: 김치를 잘게 썬다." value="${esc(s)}"><button type="button" class="x" data-act="rmRow" aria-label="삭제">✕</button></div>`;
actions.addIng = () => document.getElementById("ings").insertAdjacentHTML("beforeend", ingRow({ name: "", amount: "", price: null }));
actions.addStep = () => { const s = document.getElementById("steps"); s.insertAdjacentHTML("beforeend", stepRow("", s.children.length)); };
actions.rmRow = (el) => { const row = el.parentElement; if (row.parentElement.children.length > 1) row.remove(); renumberSteps(); updateCost(); };
actions.formChip = (el) => {
  const box = el.parentElement;
  if (box.dataset.single) box.querySelectorAll(".chip").forEach((c) => c.classList.toggle("on", c === el));
  else el.classList.toggle("on");
};
function renumberSteps() { document.querySelectorAll("#steps .num").forEach((n, i) => (n.textContent = i + 1)); }
function updateCost() {
  const prices = [...document.querySelectorAll('#ings [data-f="price"]')].map((x) => x.value).filter((v) => v !== "").map(Number);
  const el = document.getElementById("costSum"); if (el) el.textContent = prices.length ? num(prices.reduce((a, b) => a + b, 0)) + "원" : "-";
}
function readRecipeForm() {
  const pick = (g) => [...document.querySelectorAll(`[data-g="${g}"].on`)].map((c) => c.dataset.k);
  const ingredients = [...document.querySelectorAll("#ings .ingrow")].map((row) => ({
    name: row.querySelector('[data-f="name"]').value.trim(), amount: row.querySelector('[data-f="amount"]').value.trim(),
    price: row.querySelector('[data-f="price"]').value === "" ? null : Number(row.querySelector('[data-f="price"]').value),
  })).filter((i) => i.name);
  return {
    title: document.getElementById("rt").value.trim(), description: document.getElementById("rd").value.trim(),
    food_type: pick("food_type")[0], difficulty: pick("difficulty")[0], tags: pick("tags"),
    cook_minutes: Number(document.getElementById("rm").value), ingredients,
    steps: [...document.querySelectorAll('#steps [data-f="step"]')].map((x) => x.value.trim()).filter(Boolean),
    tools: document.getElementById("rtools").value.trim(),
  };
}
function bindRecipeForm(submit) {
  const img = document.getElementById("rimg");
  img.onchange = () => { if (img.files[0]) document.getElementById("rimgPv").innerHTML = `<img src="${URL.createObjectURL(img.files[0])}" alt="">`; };
  document.getElementById("ings").addEventListener("input", updateCost); updateCost();
  document.getElementById("recipeForm").onsubmit = async (e) => {
    e.preventDefault();
    const body = readRecipeForm();
    if (!body.food_type) return toast("종류를 골라 주세요");
    if (!body.difficulty) return toast("난이도를 골라 주세요");
    if (!body.ingredients.length) return toast("재료를 1개 이상 적어 주세요");
    if (!body.steps.length) return toast("조리 과정을 1개 이상 적어 주세요");
    await busy(e.submitter, async () => {
      const saved = await submit(body);
      if (img.files[0]) { const fd = new FormData(); fd.append("file", img.files[0]); await POST(`/recipes/${saved.id}/image`, fd); }
      toast("레시피를 저장했어요"); go(`/recipe/${saved.id}`);
    }).catch(() => {});
  };
}
route("/recipe-new", async (p) => recipeForm(await recipeOptions(), p.from ? { title: p.title || "" } : null, p.from ? "우승 레시피 공유" : "레시피 올리기"));
routes.at(-1).render.after = (p) => bindRecipeForm((body) => p.from ? POST(`/submissions/${p.from}/recipe`, body) : POST("/recipes", body));
route("/recipe/:id/edit", async ({ id }) => recipeForm(await recipeOptions(), await GET(`/recipes/${id}`), "레시피 수정"));
routes.at(-1).render.after = ({ id }) => bindRecipeForm((body) => PATCH(`/recipes/${id}`, body));

// ================= 대결 =================
const phaseText = (b) => b.phase === "closed" ? "종료"
  : `${b.phase_label} · ${b.phase_days_left === 0 ? "오늘 마감" : "D-" + b.phase_days_left}`;
let battleTab = null; // "low" | "mid" | "high" | "fail"

route("/battle", async () => {
  const [active, history] = await Promise.all([GET("/battles/active"), GET("/battles/history?mine=true&limit=5")]);
  const u = store.user;
  battleTab = battleTab || u.skill;
  const b = active.find((x) => x.group === battleTab) || active[0];
  const isFail = b.kind === "fail";
  const tabs = active.map((x) => `<button class="chip ${x.group === b.group ? "on" : ""}" data-act="battleTab" data-g="${x.group}">
    ${x.kind === "fail" ? "😵 망한 요리" : esc(x.group_label) + "급"}${x.group === u.skill ? " · 내 그룹" : ""}</button>`).join("");
  let action;
  if (b.can_submit) action = `<button class="btn" data-act="go" data-to="/join/${b.id}">참가하기 <span class="badge gold">+10P</span></button>`;
  else if (b.has_submitted && b.phase === "cooking") action = `<div class="banner info" style="background:rgba(255,255,255,.18);color:#fff">✅ 참가 완료! ${esc(b.vote_start_date.slice(5).replace("-", "/"))}부터 투표할 수 있어요</div>`;
  else if (!b.is_my_group && b.phase === "cooking") action = `<div class="banner" style="background:rgba(255,255,255,.18);color:#fff">다른 실력 그룹의 대결이에요 (구경만 할 수 있어요)</div>`;
  else action = "";
  return `<div class="hdr"><div class="top"><h1 class="ttl">대결</h1><span class="badge gold" style="height:30px;font-size:13px">P ${num(u.points)}</span></div>
    <div class="chips">${tabs}</div></div>
  <div class="pad stack">
    <div class="hero ${isFail ? "fail" : ""}">
      <div class="between"><span class="pill">${esc(b.kind_label)} · ${isFail ? "전체 참가" : esc(b.group_label) + "급 그룹"}</span><span class="pill">${esc(phaseText(b))}</span></div>
      <h2>${esc(b.category.name)}</h2><div style="opacity:.9">${esc(b.category.description)}</div>
      <div class="kv"><div><span>남은 기간</span><b>${b.days_left}일</b></div><div><span>참가자</span><b>${b.submission_count}명</b></div><div><span>인증 키워드</span><b>${esc(b.verification_keyword)}</b></div></div>
      <div class="small mt12" style="opacity:.85">🍳 요리 ${esc(b.start_date.slice(5))} ~ ${esc(b.cooking_end_date.slice(5))} · 🗳️ 투표 ${esc(b.vote_start_date.slice(5))} ~ ${esc(b.end_date.slice(5))}</div>
      <div class="mt16 stack">${action}
        <button class="btn" style="background:rgba(255,255,255,.2);color:#fff;box-shadow:none" data-act="go" data-to="/battle/${b.id}/entries">
          ${b.can_vote ? "출품작 보고 투표하기" : "출품작 보기"}</button></div>
    </div>
    ${b.vote_block_reason && b.phase === "voting" && !b.has_voted ? `<div class="banner warn">🗳️ ${esc(b.vote_block_reason)}</div>` : ""}
    <div class="card p"><div class="between"><h2 class="sec" style="margin:0">지난 대결 결과</h2></div>
      ${history.map((h) => `<div class="lr" data-act="go" data-to="/result/${h.id}" style="cursor:pointer">
        <span style="font-size:24px">${h.kind === "fail" ? "😵" : "🏆"}</span><div style="flex:1"><b>${esc(h.category.name)} 대결</b>
        <div class="small muted">${esc(h.start_date.slice(5))} · ${h.kind === "fail" ? "망한 요리 대회" : esc(h.group_label) + "급 그룹"}${h.is_void ? " · 무효" : ""}</div></div>${icons.chev}</div>`).join("")
        || `<p class="small muted">아직 참가한 대결이 없어요. 첫 대결에 도전해 보세요!</p>`}
    </div>
  </div>`;
}, { tab: "battle" });
actions.battleTab = (el) => { battleTab = el.dataset.g; render(); };

// ---- 참가 (12 요리 인증) ----
const joinState = { photos: {}, checks: {} };
route("/join/:id", async ({ id }) => {
  const [b, g] = await Promise.all([GET(`/battles/${id}`), GET(`/battles/${id}/shot-guide`)]);
  if (!b.can_submit) return `${header("요리 인증")}<div class="empty"><div class="ic">🙅</div>${b.has_submitted ? "이미 참가한 대결이에요" : "지금은 참가할 수 없어요"}
    <br><button class="btn ghost sm mt16" data-act="go" data-to="/battle">대결 홈으로</button></div>`;
  joinState.photos = {}; joinState.checks = {}; joinState.guide = g; joinState.battle = b;
  return `${header("요리 인증")}
  <div class="pad stack">
    <p class="muted" style="margin:0">${esc(b.category.name)} 대결 · ${b.kind === "fail" ? "망한 요리 대회" : esc(b.group_label) + "급 그룹"}</p>
    <div class="banner warn">📝 키워드 인증샷에는 <b>'${esc(g.verification_keyword)}'</b>를 종이에 써서 요리 옆에 두고 찍어 주세요</div>
    <div class="card">${g.shots.map((s) => `<div class="slot" id="slot-${s.shot_type}">
        <label class="pv" for="file-${s.shot_type}" id="pv-${s.shot_type}">📷</label>
        <input type="file" accept="image/*" capture="environment" id="file-${s.shot_type}" class="visually-hidden" data-shot="${s.shot_type}">
        <div style="flex:1;min-width:0"><div class="row"><b>${s.order}. ${esc(s.label)}</b>${s.is_random ? `<span class="badge blue">랜덤</span>` : ""}</div>
          <div class="small muted">${esc(s.guide)}</div><div class="small" id="msg-${s.shot_type}"></div></div></div>`).join('<div style="height:1px;background:#EEF1E8;margin:0 14px"></div>')}</div>
    <div class="card p stack">
      <div class="field"><label for="jt">요리명 *</label><input id="jt" class="input" maxlength="40" required placeholder="예: 치즈 스크램블 에그"></div>
      <div class="field"><label for="jd">설명</label><textarea id="jd" class="input" maxlength="300" placeholder="우유를 조금 넣어서 부드럽게 만들었어요"></textarea></div>
      <div class="field"><label for="jc">재료비 (원, 선택)</label><input id="jc" class="input" type="number" min="0" placeholder="절약한 식비 계산에 쓰여요"></div>
    </div>
    <p class="hint center">한 대결에는 한 번만 참가할 수 있어요 · 구도마다 카메라 위치를 바꿔서 새로 찍어 주세요</p>
    <div style="height:70px"></div>
  </div>
  <div class="sticky-bottom"><button class="btn" id="joinBtn" data-act="submitJoin" data-id="${b.id}">제출</button></div>`;
});
routes.at(-1).render.after = ({ id }) => {
  document.querySelectorAll("input[data-shot]").forEach((inp) => {
    inp.onchange = async () => {
      const f = inp.files[0]; const shot = inp.dataset.shot; if (!f) return;
      joinState.photos[shot] = f;
      document.getElementById("pv-" + shot).innerHTML = `<img src="${URL.createObjectURL(f)}" alt="">`;
      const msg = document.getElementById("msg-" + shot), slot = document.getElementById("slot-" + shot);
      msg.innerHTML = `<span class="muted">사진 확인 중…</span>`; slot.className = "slot";
      const fd = new FormData(); fd.append("file", f); fd.append("shot", shot);
      try {
        const r = await POST(`/battles/${id}/shot-check`, fd, { silent: true });
        joinState.checks[shot] = r.ok;
        slot.className = "slot " + (r.ok ? "ok" : "bad");
        const ai = r.ai_status === "passed" ? " · 🤖 AI 확인" : "";
        msg.innerHTML = r.ok ? `<span class="hint ok">✅ 좋아요${r.time_verified ? " · 📷 촬영 인증" : ""}${ai}</span>`
          : `<span class="hint err">❌ ${esc(r.problems.join(" / "))}</span>`;
        if (r.warnings?.length) msg.innerHTML += `<div class="hint">${esc(r.warnings.join(" / "))}</div>`;
      } catch (e) { msg.innerHTML = `<span class="hint err">${esc(e.message)}</span>`; }
    };
  });
};
actions.submitJoin = async (el) => {
  const g = joinState.guide; const missing = g.shots.filter((s) => !joinState.photos[s.shot_type]);
  if (missing.length) return toast("사진이 빠졌어요: " + missing.map((s) => s.label).join(", "));
  const title = document.getElementById("jt").value.trim(); if (!title) return toast("요리명을 입력해 주세요");
  const fd = new FormData();
  g.shots.forEach((s) => { fd.append("files", joinState.photos[s.shot_type]); fd.append("shots", s.shot_type); });
  fd.append("title", title); fd.append("description", document.getElementById("jd").value.trim());
  const cost = document.getElementById("jc").value; if (cost !== "") fd.append("ingredient_cost", cost);
  el.textContent = "올리는 중…";
  await busy(el, async () => {
    const r = await POST(`/battles/${el.dataset.id}/submissions`, fd);
    joinState.done = r; store.user = await GET("/users/me");
    go(`/joined/${el.dataset.id}`);
  }).catch(() => { el.textContent = "제출"; });
};

// ---- 참가 완료 (13) ----
route("/joined/:id", async ({ id }) => {
  const r = joinState.done; const b = await GET(`/battles/${id}`);
  const s = r?.submission;
  return `<div class="pad center" style="padding-top:70px">
    <div style="font-size:72px">🎉</div><h1 class="ttl" style="text-align:center">참가 완료!</h1>
    <span class="badge gold" style="height:30px;font-size:14px">P +${r?.points_earned ?? 1}P 적립</span>
    ${r?.leveled_up ? `<div class="banner info mt12" style="justify-content:center">🎊 레벨 업! Lv.${r.level}</div>` : ""}
    <p class="muted mt12">${esc(b.category.name)} 대결에 출품했어요.<br>${esc(b.vote_start_date.slice(5).replace("-", "/"))}부터 참가자끼리 투표해요.</p>
    ${s ? `<div class="card mt16" style="overflow:hidden;text-align:left"><img src="${esc(s.image_url)}" alt="" style="width:100%;aspect-ratio:4/3;object-fit:cover">
      <div class="p" style="padding:14px 16px"><b>${esc(s.title)}</b><div class="small muted">by 나 · 방금 전</div>
      <div class="wrap mt8"><span class="badge">출품됨</span>${s.photo_verified ? `<span class="badge blue">📷 촬영 인증</span>` : ""}${s.ai_verified ? `<span class="badge gold">🤖 AI 인증</span>` : ""}</div></div></div>` : ""}
    <div class="stack mt24"><button class="btn" data-act="go" data-to="/battle/${id}/entries">출품작 보기</button>
      <button class="btn ghost" data-act="go" data-to="/battle">대결 홈으로</button></div></div>`;
});

// ---- 출품작 / 투표 (14) ----
route("/battle/:id/entries", async ({ id }) => {
  const [b, list] = await Promise.all([GET(`/battles/${id}`), GET(`/battles/${id}/submissions`)]);
  const info = b.phase === "voting"
    ? (b.can_vote ? `<div class="banner info">🗳️ 1인 1표 · 마음에 드는 한 접시를 골라주세요</div>` : `<div class="banner warn">${esc(b.vote_block_reason)}</div>`)
    : b.phase === "cooking" ? `<div class="banner info">🍳 요리 기간이에요. 투표는 ${esc(b.vote_start_date.slice(5).replace("-", "/"))}부터 참가자만 할 수 있어요</div>`
    : `<div class="banner info">🏁 끝난 대결이에요 <button class="btn sm" style="margin-left:auto;height:32px" data-act="go" data-to="/result/${b.id}">결과 보기</button></div>`;
  return `${header("투표", { right: `<span class="badge">1인 1표</span>` })}
  <div class="pad stack">
    <div><h2 class="ttl" style="font-size:22px">${esc(b.category.name)} 대결</h2><p class="muted" style="margin:4px 0 0">출품작 ${list.length}개 · ${esc(phaseText(b))}</p></div>
    ${info}
    <div class="grid2">${list.map((s) => `<div class="card entry" data-act="go" data-to="/entry/${s.id}">
      <div class="ph">${s.image_url ? `<img src="${esc(s.image_url)}" alt="${esc(s.title)}" loading="lazy">` : "🍽️"}</div>
      <div class="bd"><b style="font-size:14px">${esc(s.title)}</b><span class="small muted">by ${s.is_mine ? "나" : esc(s.nickname)}${s.rating_count ? ` · ★${s.rating_avg}` : ""}</span>
        <div class="between"><span class="small b">🗳️ ${s.vote_count ?? "?"}</span>
        ${s.is_mine ? `<span class="badge">내 작품</span>` : s.has_voted ? `<span class="badge gold">✓ 투표함</span>`
          : b.can_vote ? `<button class="btn sm" style="height:32px;padding:0 12px" data-act="vote" data-id="${s.id}">투표하기</button>` : ""}</div></div></div>`).join("")}</div>
    ${list.length ? "" : `<div class="empty"><div class="ic">🍳</div>아직 출품작이 없어요</div>`}
    <p class="hint center">1인 1표 · 자기 작품에는 투표할 수 없어요 · 참가자만 투표할 수 있어요</p>
  </div>`;
});
actions.vote = async (el, e) => {
  e.stopPropagation();
  if (!confirm("이 작품에 투표할까요? (1인 1표, 되돌릴 수 없어요)")) return;
  await busy(el, () => POST(`/submissions/${el.dataset.id}/vote`)).then(() => { toast("투표했어요!"); render(); }).catch(() => {});
};

// ---- 작품 상세 + 평가(별점) ----
route("/entry/:id", async ({ id }) => {
  const [s, cm] = await Promise.all([GET(`/submissions/${id}`), GET(`/submissions/${id}/comments`)]);
  const b = await GET(`/battles/${s.battle_id}`);
  const mine = cm.comments.find((c) => c.is_mine);
  return `${header(s.title)}
  <div class="shots">${s.images.map((im) => `<figure><img src="${esc(im.url)}" alt="${esc(im.shot_label)}"><figcaption><span class="badge">${esc(im.shot_label || "사진")}</span></figcaption></figure>`).join("")}</div>
  <div class="pad stack mt12">
    <div class="card p stack">
      <div class="row"><span class="av sm">${initial(s.nickname)}</span><b data-act="go" data-to="/user/${s.user_id}" style="cursor:pointer">${esc(s.is_mine ? "나" : s.nickname)}</b><span class="small muted">Lv.${s.user_level}</span></div>
      <div class="wrap">${s.photo_verified ? `<span class="badge blue">📷 촬영 인증</span>` : ""}${s.ai_verified ? `<span class="badge gold">🤖 AI 인증</span>` : ""}
        <span class="badge">🗳️ ${s.vote_count ?? "?"}표</span>${cm.summary.count ? `<span class="badge gold">★ ${cm.summary.average} (${cm.summary.count})</span>` : ""}</div>
      ${s.description ? `<p style="margin:0">${esc(s.description)}</p>` : ""}
      ${!s.is_mine && !s.has_voted && b.can_vote ? `<button class="btn" data-act="vote" data-id="${s.id}">투표하기</button>` : ""}
    </div>
    <div class="card p"><h2 class="sec">평가 ${cm.summary.count}</h2>
      ${!s.is_mine ? `<form id="rateForm" class="stack" style="margin-bottom:12px">
        <div class="starpick" id="starpick">${[1, 2, 3, 4, 5].map((n) => `<button type="button" data-act="pickStar" data-n="${n}" class="${mine && mine.rating >= n ? "on" : ""}" aria-label="${n}점">★</button>`).join("")}</div>
        <div class="row"><input class="input" id="rateText" maxlength="500" placeholder="평가를 남겨 주세요" value="${esc(mine?.content)}"><button class="btn sm" style="height:52px">${mine ? "수정" : "등록"}</button></div></form>` : ""}
      ${cm.comments.map((c) => `<div class="lr" style="align-items:flex-start"><span class="av sm">${initial(c.nickname)}</span>
        <div style="flex:1"><div class="between"><b class="small">${esc(c.nickname)}</b><span class="small muted">${esc(c.created_at_display)}${c.is_edited ? " (수정됨)" : ""}</span></div>
        ${c.rating ? `<span class="stars">${stars(c.rating)}</span>` : ""}<div style="font-size:14px">${esc(c.content)}</div></div>
        ${c.is_mine ? `<button class="x" data-act="delComment" data-id="${c.id}" aria-label="삭제">✕</button>` : ""}</div>`).join("") || `<p class="small muted">아직 평가가 없어요</p>`}
    </div>
    ${!s.is_mine ? `<button class="btn ghost sm" style="align-self:center" data-act="report" data-id="${s.id}">🚩 신고하기</button>` : ""}
  </div>`;
});
routes.at(-1).render.after = ({ id }) => {
  const f = document.getElementById("rateForm"); if (!f) return;
  const starsOn = () => document.querySelectorAll("#starpick .on").length;
  f.onsubmit = async (e) => {
    e.preventDefault();
    const rating = starsOn(), content = document.getElementById("rateText").value.trim();
    if (!rating) return toast("별점을 골라 주세요"); if (!content) return toast("평가 내용을 입력해 주세요");
    const mine = await GET(`/submissions/${id}/comments/mine`);
    await busy(e.submitter, () => mine ? PATCH(`/comments/${mine.id}`, { rating, content }) : POST(`/submissions/${id}/comments`, { rating, content }))
      .then(() => { toast("평가를 남겼어요"); render(); }).catch(() => {});
  };
};
actions.pickStar = (el) => { const n = +el.dataset.n; document.querySelectorAll("#starpick button").forEach((b) => b.classList.toggle("on", +b.dataset.n <= n)); };
actions.delComment = async (el) => { if (!confirm("평가를 삭제할까요?")) return; await DEL(`/comments/${el.dataset.id}`); render(); };
actions.report = async (el) => {
  const reason = prompt("신고 이유를 적어 주세요 (예: 인터넷 사진 같아요)"); if (reason === null) return;
  await POST(`/submissions/${el.dataset.id}/report`, { reason }).then(() => toast("신고했어요. 검토할게요")).catch(() => {});
};

// ---- 결과 (15) ----
route("/result/:id", async ({ id }) => {
  const r = await GET(`/battles/${id}/results`);
  const b = r.battle, me = r.my_result, P = r.podium;
  const pod = (e, h) => e ? `<div class="pod"><span class="av">${initial(e.nickname)}</span><span>${esc(e.nickname)}${me && e.submission_id === me.submission_id ? " (나)" : ""}</span>
    <div class="pbar" style="height:${h}px">${e.rank}</div></div>` : `<div class="pod"></div>`;
  return `${header("대결 결과")}
  <div class="pad stack">
    <p class="muted" style="margin:0">${esc(b.category.name)} 대결 · ${b.kind === "fail" ? "망한 요리 대회" : esc(b.group_label) + "급 그룹"} · 참가자 ${b.submission_count}명</p>
    ${r.is_void ? `<div class="banner warn">참가자가 ${3}명보다 적어 무효 처리됐어요. 참가 포인트만 지급돼요</div>`
      : `<div class="pods">${pod(P[1], 90)}${pod(P[0], 130)}${pod(P[2], 70)}</div>`}
    ${me ? `<div class="card p between"><span><span class="muted small">내 순위</span><br><b style="font-size:22px">${me.rank}등</b></span>
      <span class="badge gold" style="height:32px;font-size:15px">P +${me.points_earned}P</span></div>
      ${me.leveled_up ? `<div class="banner info" data-act="go" data-to="/shop" style="cursor:pointer">🎊 레벨 업! Lv.${me.level_before} → Lv.${me.level_after} · 상점에서 새 기프티콘이 열렸어요</div>` : ""}
      ${me.can_share_recipe ? (P[0]?.recipe_id ? `<button class="btn ghost" data-act="go" data-to="/recipe/${P[0].recipe_id}">내가 공유한 레시피 보기</button>`
        : `<button class="btn" data-act="go" data-to="/recipe-new?from=${me.submission_id}&title=${encodeURIComponent(P[0]?.title || "")}">🏆 우승 레시피 공유하기</button>`) : ""}` : ""}
    <div class="card p"><div class="between"><h2 class="sec" style="margin:0">TOP 10</h2><span class="small muted">투표 수 기준</span></div>
      ${r.entries.slice(0, 10).map((e) => `<div class="lr"><span class="rk">${e.rank}</span><span class="av sm">${initial(e.nickname)}</span>
        <span style="flex:1;cursor:pointer" data-act="go" data-to="/entry/${e.submission_id}">${esc(e.nickname)}${me && e.submission_id === me.submission_id ? " (나)" : ""}
        ${e.recipe_id ? ` <span class="badge gold" data-act="go" data-to="/recipe/${e.recipe_id}">레시피 공유</span>` : ""}</span><b>${e.vote_count}표</b></div>`).join("") || `<p class="small muted">출품작이 없어요</p>`}
    </div>
  </div>`;
});

// ================= 홈 (03) =================
route("/home", async () => {
  const [h, rank] = await Promise.all([GET("/users/me/home"), GET("/friends/ranking").catch(() => [])]);
  const u = h.user; store.user = u;
  return `<div class="hdr"><div class="top"><h1 class="ttl">요리왕</h1></div></div>
  <div class="pad stack">
    <div class="card p stack">
      <div class="row"><span class="av lg">${initial(u.nickname)}</span><div style="flex:1"><b style="font-size:20px">${esc(u.nickname)}</b>
        <div class="row small mt8"><span class="badge">Lv.${u.level}</span><span class="muted">${esc(u.skill_label)}급 대결 그룹</span></div></div></div>
      <div class="between"><span class="muted small">보유 포인트</span><b style="font-size:22px">${num(u.points)}P</b></div>
      <div class="bar"><i style="width:${Math.round(u.level_progress * 100)}%"></i></div>
      <div class="between small"><span class="muted">다음 레벨까지 ${u.points_to_next_level}P</span><b>Lv.${u.level + 1}</b></div>
    </div>
    <div class="row" style="align-items:stretch">
      <div class="card p" style="flex:1"><span class="small muted">이번 달 요리</span><div class="b" style="font-size:24px">${h.this_month.cook_count}회</div></div>
      <div class="card p" style="flex:1"><span class="small muted">절약한 식비</span><div class="b" style="font-size:24px">${num(h.this_month.saved_money)}원</div></div>
    </div>
    <div class="card p"><div class="between"><h2 class="sec" style="margin:0">참가 이력</h2><a class="small b" href="#/battle">대결 보기 ›</a></div>
      ${h.history.slice(0, 6).map((x) => `<div class="lr" data-act="go" data-to="${x.is_closed ? "/result/" + x.battle_id : "/battle/" + x.battle_id + "/entries"}" style="cursor:pointer">
        <span style="font-size:22px">${x.kind === "fail" ? "😵" : "🍳"}</span><div style="flex:1"><b>${esc(x.category_name)} 대결</b>
        <div class="small muted">${esc(x.start_date.slice(5))} · ${esc(x.title)}</div></div>
        <span class="badge ${x.rank && x.rank <= 3 ? "gold" : ""}">${x.rank ? x.rank + "등" : x.is_closed ? (x.is_void ? "무효" : "참가") : "진행 중"}</span></div>`).join("")
        || `<div class="empty" style="padding:20px"><p>첫 대결에 참가해 보세요!</p><button class="btn sm" data-act="go" data-to="/battle">대결 바로가기</button></div>`}
    </div>
    <div class="card p"><div class="between"><h2 class="sec" style="margin:0">친구 랭킹</h2><a class="small b" href="#/friends">친구 ›</a></div>
      ${rank.length > 1 ? rank.slice(0, 5).map((r) => `<div class="lr"><span class="rk">${r.rank}</span><span class="av sm">${initial(r.nickname)}</span>
        <span style="flex:1">${esc(r.nickname)}${r.is_me ? " (나)" : ""} <span class="small muted">Lv.${r.level}</span></span><b>${num(r.total_points)}P</b></div>`).join("")
        : `<p class="small muted">친구를 추가하고 순위를 겨뤄 보세요 · 내 초대 코드 <b>${esc(u.invite_code)}</b></p>`}
    </div>
    <button class="btn ghost" data-act="go" data-to="/profile-edit">정보 수정</button>
  </div>`;
}, { tab: "home" });

// ================= 상점 =================
route("/shop", async () => {
  const [u, items] = await Promise.all([refreshMe(), GET("/shop/items")]);
  return `<div class="hdr"><div class="top"><h1 class="ttl">상점</h1><span class="badge gold" style="height:30px;font-size:13px">P ${num(u.points)}</span></div></div>
  <div class="pad stack">
    <div class="banner info">🎁 Lv.${u.level} · 레벨이 오르면 더 많은 기프티콘이 열려요</div>
    <div class="card p"><h2 class="sec">기프티콘</h2>
      ${items.map((it) => `<div class="lr"><span style="font-size:28px">🎁</span><div style="flex:1"><b>${esc(it.name)}</b>
        <div class="small muted">${num(it.price)}P${it.min_level > 1 ? ` · Lv.${it.min_level}+` : ""}${it.stock != null ? ` · 남은 ${it.stock}개` : ""}</div>
        ${it.blocked_reason ? `<div class="small" style="color:#8A5A12">${esc(it.blocked_reason)}</div>` : ""}</div>
        <button class="btn sm" ${it.can_exchange ? "" : "disabled"} data-act="shopSheet" data-id="${it.id}" data-name="${esc(it.name)}" data-price="${it.price}">교환</button></div>`).join("")
        || `<p class="small muted">상품이 없어요</p>`}
    </div>
    <p class="hint center">포인트는 대결 참가(+10P)·투표(+2P)·순위 보상으로 모여요 · 교환한 기프티콘은 추후 발송돼요 (MVP)</p>
  </div>`;
}, { tab: "shop" });
actions.shopSheet = (el) => {
  const price = +el.dataset.price, have = store.user.points;
  document.getElementById("sheet-root").innerHTML = `<div class="sheet-bg" data-act="closeSheet"><div class="sheet" data-stop="1">
    <h2 class="ttl-s">${esc(el.dataset.name)}</h2><p class="muted small">교환하면 포인트가 바로 차감돼요</p>
    <div class="dl"><span>필요 포인트</span><b>${num(price)}P</b></div><div class="dl"><span>보유 포인트</span><b>${num(have)}P</b></div>
    <div class="dl" style="border-top:1px solid #EEF1E8"><span>교환 후</span><b>${num(have - price)}P</b></div>
    <div class="row mt16"><button class="btn ghost" data-act="closeSheet">취소</button><button class="btn" data-act="doExchange" data-id="${el.dataset.id}">교환하기</button></div></div></div>`;
};
actions.closeSheet = (el, e) => { if (e.target.closest("[data-stop]") && el.classList.contains("sheet-bg")) return; document.getElementById("sheet-root").innerHTML = ""; };
actions.doExchange = async (el) => {
  await busy(el, () => POST(`/shop/items/${el.dataset.id}/exchange`)).then((r) => {
    document.getElementById("sheet-root").innerHTML = `<div class="sheet-bg"><div class="sheet center"><div style="font-size:64px">🎉</div>
      <h2 class="ttl-s" style="text-align:center">교환 완료!</h2><p class="muted">${esc(r.item_name)} · 남은 포인트 ${num(r.points_left)}P</p>
      <button class="btn mt16" data-act="closeSheetReload">확인</button></div></div>`;
  }).catch(() => {});
};
actions.closeSheetReload = () => { document.getElementById("sheet-root").innerHTML = ""; render(); };

// ================= 메뉴 (10) =================
route("/menu", async () => {
  const [u, saved, recent, mine] = await Promise.all([refreshMe(), GET("/users/me/saved-recipes"), GET("/users/me/recent-recipes"), GET("/users/me/recipes")]);
  const reqs = await GET("/friends/requests").catch(() => []);
  const row = (to, label, right = "") => `<a class="menu-row" href="#${to}">${label}<span class="r">${right}</span>${icons.chev}</a>`;
  return `<div class="hdr"><div class="top"><h1 class="ttl">메뉴</h1></div></div>
  <div class="pad stack">
    <div class="card p row"><span class="av lg">${initial(u.nickname)}</span><div><b style="font-size:18px">${esc(u.nickname)}</b> <span class="badge">Lv.${u.level}</span>
      <div class="small muted">${esc(u.skill_label)}급 대결 그룹 · ${num(u.points)}P</div></div></div>
    <div class="card">
      ${row("/list/saved", "📌 저장한 레시피", saved.length + "개")}
      ${row("/list/recent", "🕘 최근 본 레시피", recent.length + "개")}
      ${row("/list/mine", "📝 내가 올린 레시피", mine.length + "개")}
      ${row("/list/reviews", "💬 후기 모음")}
      ${row("/friends", "👥 친구", reqs.length ? `<span class="badge red">요청 ${reqs.length}</span>` : "")}
    </div>
    ${saved.length ? "" : `<div class="card p center"><p class="muted">아직 저장한 레시피가 없어요</p><button class="btn ghost sm" data-act="go" data-to="/recipes">레시피 둘러보기</button></div>`}
    <div class="card">
      <div class="menu-row">🔔 알림 설정<button class="switch ${u.notifications_enabled ? "on" : ""}" style="margin-left:auto" data-act="toggleNoti" aria-label="알림"></button></div>
      <button class="menu-row" data-act="tutAgain">📖 튜토리얼 다시 보기</button>
      ${row("/profile-edit", "⚙️ 정보 수정")}
      ${u.is_admin ? row("/admin", "🛠️ 관리자 (시연용)") : ""}
      <button class="menu-row" data-act="logout" style="color:var(--red)">로그아웃</button>
    </div>
  </div>`;
}, { tab: "menu" });
actions.toggleNoti = async (el) => { const r = await PATCH("/users/me", { notifications_enabled: !store.user.notifications_enabled }); store.user = r.user; el.classList.toggle("on", r.user.notifications_enabled); };
actions.tutAgain = async () => { store.user = await PATCH("/users/me/tutorial", { step: 0, completed: false }); go("/onboarding"); };
actions.logout = () => { store.token = null; store.user = null; go("/login"); };

route("/list/:kind", async ({ kind }) => {
  if (kind === "reviews") {
    const rv = await GET("/reviews?limit=50");
    return `${header("후기 모음")}<div class="pad stack">${rv.map((v) => `<div class="card p" data-act="go" data-to="/recipe/${v.recipe_id}" style="cursor:pointer">
      <div class="between small"><b>${esc(v.nickname)}</b><span class="muted">${esc(v.recipe_title)}</span></div><div class="mt8">${esc(v.content)}</div></div>`).join("")
      || `<div class="empty"><div class="ic">💬</div>아직 후기가 없어요</div>`}</div>`;
  }
  const map = { saved: ["저장한 레시피", "/users/me/saved-recipes"], recent: ["최근 본 레시피", "/users/me/recent-recipes"], mine: ["내가 올린 레시피", "/users/me/recipes"] };
  const [title, path] = map[kind] || map.saved;
  const list = await GET(path);
  return `${header(title)}<div class="pad stack">${list.map(recipeCard).join("") || `<div class="empty"><div class="ic">📭</div>아직 없어요
    <br><button class="btn ghost sm mt16" data-act="go" data-to="${kind === "mine" ? "/recipe-new" : "/recipes"}">${kind === "mine" ? "레시피 올리기" : "레시피 둘러보기"}</button></div>`}</div>`;
});

// ================= 정보 수정 (08) =================
route("/profile-edit", async () => {
  const u = await refreshMe();
  return `${header("정보 수정")}
  <form id="peForm" class="pad stack">
    <div class="center"><span class="av lg" style="margin:0 auto">${initial(u.nickname)}</span></div>
    <div class="field"><label for="pn">닉네임</label><input id="pn" class="input" maxlength="12" value="${esc(u.nickname)}"></div>
    <div class="field"><label>이메일</label><input class="input" value="${esc(u.email)}" disabled></div>
    <div class="field"><label for="pc">현재 비밀번호 (비밀번호 변경 시)</label><input id="pc" class="input" type="password" autocomplete="current-password"></div>
    <div class="field"><label for="pw">새 비밀번호</label><input id="pw" class="input" type="password" autocomplete="new-password" placeholder="8자 이상, 영문+숫자"></div>
    <div class="field"><label>요리 실력</label><div class="wrap">${["low", "mid", "high"].map((k) => `<span class="chip ${u.skill === k ? "on" : ""}">${{ low: "초급", mid: "중급", high: "상급" }[k]}</span>`).join("")}</div>
      <span class="hint">요리 실력(대결 그룹)은 가입 후 바꿀 수 없어요</span></div>
    <div class="field"><label>내 초대 코드</label><input class="input" value="${esc(u.invite_code)}" readonly></div>
    <button class="btn mt8" type="submit">저장</button>
    <button class="btn ghost" type="button" data-act="logoutAll">모든 기기에서 로그아웃</button>
  </form>`;
});
routes.at(-1).render.after = () => {
  document.getElementById("peForm").onsubmit = async (e) => {
    e.preventDefault();
    const body = {}; const n = document.getElementById("pn").value.trim();
    if (n && n !== store.user.nickname) body.nickname = n;
    const np = document.getElementById("pw").value;
    if (np) { body.new_password = np; body.current_password = document.getElementById("pc").value; }
    if (!Object.keys(body).length) return toast("바뀐 내용이 없어요");
    await busy(e.submitter, async () => {
      const r = await PATCH("/users/me", body); store.user = r.user;
      if (r.access_token) store.token = r.access_token; // 비밀번호 변경 시 새 토큰
      toast("저장했어요"); back();
    }).catch(() => {});
  };
};
actions.logoutAll = async () => { if (!confirm("모든 기기에서 로그아웃할까요?")) return; await POST("/auth/logout-all"); actions.logout(); };

// ================= 친구 =================
route("/friends", async () => {
  const [friends, recv, sent, rank, feed] = await Promise.all([GET("/friends"), GET("/friends/requests"), GET("/friends/requests?box=sent"),
    GET("/friends/ranking"), GET("/friends/activity?limit=10")]);
  return `${header("친구")}
  <div class="pad stack">
    <label class="search" style="margin:0">${icons.search}<input id="fq" placeholder="닉네임으로 친구 찾기" aria-label="친구 검색"></label>
    <div id="fres" class="stack"></div>
    ${recv.length ? `<div class="card p"><h2 class="sec">받은 요청 ${recv.length}</h2>${recv.map((r) => `<div class="lr"><span class="av sm">${initial(r.from_user.nickname)}</span>
      <span style="flex:1">${esc(r.from_user.nickname)} <span class="small muted">Lv.${r.from_user.level}</span></span>
      <button class="btn sm" data-act="frAccept" data-id="${r.id}">수락</button><button class="btn ghost sm" data-act="frReject" data-id="${r.id}">거절</button></div>`).join("")}</div>` : ""}
    <div class="card p"><h2 class="sec">친구 랭킹</h2>${rank.map((r) => `<div class="lr"><span class="rk">${r.rank}</span><span class="av sm">${initial(r.nickname)}</span>
      <span style="flex:1;cursor:pointer" data-act="go" data-to="/user/${r.user_id}">${esc(r.nickname)}${r.is_me ? " (나)" : ""} <span class="small muted">Lv.${r.level} · 우승 ${r.win_count}</span></span><b>${num(r.total_points)}P</b></div>`).join("")}</div>
    <div class="card p"><h2 class="sec">친구 소식</h2>${feed.map((f) => `<div class="lr" data-act="go" data-to="/entry/${f.submission_id}" style="cursor:pointer">
      <span class="av sm">${initial(f.user.nickname)}</span><span style="flex:1;font-size:14px">${esc(f.message)}<div class="small muted">${esc(f.created_at_display)}</div></span></div>`).join("")
      || `<p class="small muted">친구들의 새 소식이 없어요</p>`}</div>
    <div class="card p"><h2 class="sec">친구 ${friends.length}</h2>${friends.map((f) => `<div class="lr"><span class="av sm">${initial(f.nickname)}</span>
      <span style="flex:1;cursor:pointer" data-act="go" data-to="/user/${f.user_id}">${esc(f.nickname)} <span class="small muted">Lv.${f.level} · ${esc(f.skill_label)}급</span>
      <div class="small muted">${f.last_cooked_at ? "마지막 요리 " + esc(f.last_cooked_at) : "아직 요리 기록 없음"}</div></span></div>`).join("") || `<p class="small muted">아직 친구가 없어요. 위에서 닉네임으로 찾아보세요</p>`}</div>
    ${sent.length ? `<div class="card p"><h2 class="sec">보낸 요청</h2>${sent.map((r) => `<div class="lr"><span style="flex:1">${esc(r.to_user.nickname)}</span>
      <button class="btn ghost sm" data-act="frCancel" data-id="${r.id}">취소</button></div>`).join("")}</div>` : ""}
    <p class="hint center">내 초대 코드 <b>${esc(store.user.invite_code)}</b> — 친구가 가입할 때 입력하면 자동으로 친구가 돼요</p>
  </div>`;
});
routes.at(-1).render.after = () => {
  document.getElementById("fq").addEventListener("input", debounce(async (e) => {
    const q = e.target.value.trim(); const box = document.getElementById("fres"); if (!box) return;
    if (!q) { box.innerHTML = ""; return; }
    const list = await GET("/users/search" + qs({ nickname: q }), { silent: true }).catch(() => []);
    box.innerHTML = `<div class="card p">${list.map(friendRow).join("") || `<p class="small muted">검색 결과가 없어요</p>`}</div>`;
  }, 300));
};
const relationButton = (u, onProfile = false) => ({
  none: `<button class="btn sm" data-act="frRequest" data-id="${u.user_id}">친구 요청</button>`,
  request_sent: `<button class="btn ghost sm" data-act="frCancel" data-id="${u.request_id}">요청 취소</button>`,
  request_received: `<button class="btn sm" data-act="frAccept" data-id="${u.request_id}">수락</button>`,
  friend: onProfile ? `<button class="btn danger sm" data-act="frRemove" data-id="${u.user_id}">친구 삭제</button>` : `<span class="badge">친구 ✓</span>`,
  self: onProfile ? "" : `<span class="badge">나</span>`,
}[u.relation] || "");
const friendRow = (u) => `<div class="lr"><span class="av sm">${initial(u.nickname)}</span><span style="flex:1;cursor:pointer" data-act="go" data-to="/user/${u.user_id}">${esc(u.nickname)}
    <span class="small muted">Lv.${u.level} · ${esc(u.skill_label)}급</span></span>${relationButton(u)}</div>`;
actions.frRequest = async (el) => { const r = await POST("/friends/requests", { user_id: +el.dataset.id }); toast(r.message); render(); };
actions.frAccept = async (el) => { const r = await POST(`/friends/requests/${el.dataset.id}/accept`); toast(r.message); render(); };
actions.frReject = async (el) => { await POST(`/friends/requests/${el.dataset.id}/reject`); render(); };
actions.frCancel = async (el) => { await DEL(`/friends/requests/${el.dataset.id}`); render(); };
actions.frRemove = async (el) => { if (!confirm("친구를 삭제할까요?")) return; await DEL(`/friends/${el.dataset.id}`); render(); };

route("/user/:id", async ({ id }) => {
  const p = await GET(`/users/${id}/profile`);
  const btn = relationButton(p, true);
  return `${header(p.nickname)}
  <div class="pad stack">
    <div class="card p stack center"><span class="av lg" style="margin:0 auto">${initial(p.nickname)}</span><b style="font-size:20px">${esc(p.nickname)}</b>
      <div class="row" style="justify-content:center"><span class="badge">Lv.${p.level}</span><span class="badge blue">${esc(p.skill_label)}급</span></div>
      <div class="row" style="align-items:stretch"><div class="stat"><span>참가</span><b>${p.battle_count}회</b></div><div class="stat"><span>우승</span><b>${p.win_count}회</b></div><div class="stat"><span>친구</span><b>${p.friend_count}명</b></div></div>
      <div>${btn}</div></div>
    <div class="grid2">${p.recent_submissions.map((s) => `<div class="card entry" data-act="go" data-to="/entry/${s.submission_id}"><div class="ph"><img src="${esc(s.image_url)}" alt="" loading="lazy"></div>
      <div class="bd"><b class="small">${esc(s.title)}</b><span class="small muted">${esc(s.category_name)}</span></div></div>`).join("")}</div>
  </div>`;
});

// ================= 관리자 (시연용) =================
route("/admin", async () => {
  if (!store.user.is_admin) return `<div class="empty">관리자만 볼 수 있어요</div>`;
  const [active, ai] = await Promise.all([GET("/battles/active"), GET("/admin/ai/status").catch(() => null)]);
  return `${header("관리자 (시연용)")}
  <div class="pad stack">
    <div class="banner warn">날짜를 기다리지 않고 요리 기간 → 투표 기간 → 종료를 바로 넘길 수 있어요</div>
    ${active.map((b) => `<div class="card p admin stack"><div class="between"><b>${esc(b.kind_label)} · ${esc(b.kind === "fail" ? "전체" : b.group_label + "급")}</b><span class="badge">${esc(phaseText(b))}</span></div>
      <div class="small" style="opacity:.8">${esc(b.category.name)} · 참가 ${b.submission_count}명 · #${b.id}</div>
      <div class="row"><button class="btn sm" data-act="adPhase" data-id="${b.id}" data-p="cooking" ${b.phase === "cooking" ? "disabled" : ""}>요리 기간</button>
        <button class="btn sm" data-act="adPhase" data-id="${b.id}" data-p="voting" ${b.phase === "voting" ? "disabled" : ""}>투표 기간</button>
        <button class="btn sm" data-act="adClose" data-id="${b.id}">종료·결과</button></div></div>`).join("")}
    ${ai ? `<div class="card p small">🤖 이미지 인식 AI: <b>${ai.enabled ? "켜짐" : "꺼짐"}</b> · 모드 ${esc(ai.mode)} · API 키 ${ai.api_key_set ? "설정됨" : "없음"}</div>` : ""}
  </div>`;
});
actions.adPhase = async (el) => { await POST(`/admin/battles/${el.dataset.id}/phase`, { phase: el.dataset.p }); toast("기간을 바꿨어요"); render(); };
actions.adClose = async (el) => {
  if (!confirm("이 대결을 지금 종료하고 포인트를 지급할까요?")) return;
  await POST(`/admin/battles/${el.dataset.id}/close`); toast("종료했어요. 새 대결이 열려요"); go(`/result/${el.dataset.id}`);
};

// ================= 시작 =================
if (!location.hash) location.hash = store.token ? "/battle" : "/login";
render();
