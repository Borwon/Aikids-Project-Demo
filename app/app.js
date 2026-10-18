/* VisaConnect Case Copilot -- shared frontend helpers.
   No framework, no CDN: fonts and icons ship with the app so it renders offline. */

const IS_HTTP = location.protocol === "http:" || location.protocol === "https:";
const STAFF_KEY = "vc_staff_id";
const STAFF_IDS = Array.from({ length: 12 }, (_, i) => `ST-${String(i + 1).padStart(3, "0")}`);

/* ---------- tiny dom utils ---------- */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const clear = (node) => { while (node.firstChild) node.removeChild(node.firstChild); };

/* ---------- icons ----------
   One hand-drawn set on a 24px grid, one stroke weight (1.7), round joins, so
   mixed icons never look mismatched. `currentColor` keeps them themeable. */
const ICONS = {
  spark: '<path d="M12 3.6l1.9 5.4 5.4 1.9-5.4 1.9L12 18.2l-1.9-5.4L4.7 10.9l5.4-1.9z"/>',
  checkCircle: '<circle cx="12" cy="12" r="8.6"/><path d="M8.4 12.3l2.5 2.5 4.7-5"/>',
  search: '<circle cx="11" cy="11" r="6.8"/><path d="M16.2 16.2L20.5 20.5"/>',
  queue: '<path d="M4 6.5h16M4 12h16M4 17.5h10"/>',
  clipboard: '<rect x="4.6" y="5" width="14.8" height="15.4" rx="2.4"/><path d="M9 5V3.9h6V5"/><path d="M8.6 10.8h6.8M8.6 14.4h4.4"/>',
  alert: '<path d="M12 4.3l8.7 15.4H3.3z"/><path d="M12 10v4.1"/><path d="M12 17.1v.01"/>',
  info: '<circle cx="12" cy="12" r="8.6"/><path d="M12 11.2v5"/><path d="M12 8v.01"/>',
  check: '<path d="M5 12.6l4.6 4.6L19 7.4"/>',
  pencil: '<path d="M4.4 19.6h4L19 9l-4-4L4.4 15.6z"/><path d="M14.4 5.6l4 4"/>',
  x: '<path d="M6.4 6.4l11.2 11.2M17.6 6.4L6.4 17.6"/>',
  clock: '<circle cx="12" cy="12" r="8.6"/><path d="M12 7.4V12l3.1 2"/>',
  user: '<circle cx="12" cy="8.6" r="3.5"/><path d="M5.2 20c0-3.5 3-5.4 6.8-5.4s6.8 1.9 6.8 5.4"/>',
  file: '<path d="M7 3.6h6.6l4.4 4.4V20.4H7z"/><path d="M13.6 3.6V8H18"/><path d="M9.6 13h5M9.6 16.2h3.4"/>',
  plane: '<path d="M20.8 3.4L11 13.2"/><path d="M20.8 3.4l-6.6 17.2-3-7.6-7.6-3z"/>',
  message: '<path d="M20 11.8c0 3.7-3.6 6.7-8 6.7-1 0-2-.2-2.9-.5L5 20l1.4-3.3A6.4 6.4 0 0 1 4 11.8c0-3.7 3.6-6.7 8-6.7s8 3 8 6.7z"/>',
  star: '<path d="M12 4.4l2.4 4.9 5.4.8-3.9 3.8 1 5.4-4.9-2.6-4.9 2.6 1-5.4L4.2 10l5.4-.8z"/>',
  arrowLeft: '<path d="M19 12H5.4"/><path d="M11 5.8L5 12l6 6.2"/>',
  refresh: '<path d="M20 12a8 8 0 1 1-2.6-5.9"/><path d="M20.2 4.4v5.4h-5.4"/>',
  inbox: '<path d="M4 13.4h3.8l1.4 2.8h5.6l1.4-2.8H20"/><path d="M4 13.4L6.4 5.4h11.2L20 13.4v5.6H4z"/>',
  send: '<path d="M4.4 12l15.2-7.4-7.4 15.2-1.9-6z"/>',
  lock: '<rect x="5" y="10.4" width="14" height="9.8" rx="2.4"/><path d="M8.4 10.4V7.8a3.6 3.6 0 0 1 7.2 0v2.6"/>',
};

function icon(name, cls = "") {
  const body = ICONS[name] || "";
  return `<svg class="ico ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" ` +
    `stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${body}</svg>`;
}

function badge(text, kind = "neutral", withDot = false) {
  return `<span class="badge badge-${kind}">${withDot ? '<span class="dot"></span>' : ""}${esc(text)}</span>`;
}

function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return esc(iso);
  return d.toLocaleString(undefined, { year: "numeric", month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function fmtShort(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return isNaN(d) ? esc(iso) : d.toLocaleDateString(undefined, { month: "short", day: "2-digit" });
}

function toast(msg) {
  let t = $("#toast");
  if (!t) { t = document.createElement("div"); t.id = "toast"; t.className = "toast"; t.setAttribute("role", "status"); document.body.appendChild(t); }
  t.innerHTML = icon("check") + `<span>${esc(msg)}</span>`;
  requestAnimationFrame(() => t.classList.add("show"));
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove("show"), 2800);
}

/* ---------- staff identity (mock login) ---------- */
function getStaff() {
  const v = localStorage.getItem(STAFF_KEY);
  if (v && STAFF_IDS.includes(v)) return v;
  localStorage.setItem(STAFF_KEY, STAFF_IDS[0]);
  return STAFF_IDS[0];
}
function setStaff(id) { localStorage.setItem(STAFF_KEY, id); }

/* ---------- api ---------- */
async function getCases() {
  const url = IS_HTTP ? "/api/cases" : "../data/cases.json";
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to load cases (${res.status})`);
  const data = await res.json();
  return Array.isArray(data) ? data : data.cases;
}
async function getApprovals() {
  const res = await fetch("/api/approvals");
  if (!res.ok) throw new Error(`Failed to load approvals (${res.status})`);
  return res.json();
}
async function getBias() {
  const res = await fetch("/api/bias");
  if (!res.ok) return null;
  return res.json();
}
async function getDraft(caseId) {
  const res = await fetch(`/api/draft?case_id=${encodeURIComponent(caseId)}`);
  if (!res.ok) return null;
  return res.json();
}
async function postApproval(entry) {
  if (!IS_HTTP) { toast("Open via server.py to record approvals."); throw new Error("offline"); }
  const res = await fetch("/api/approvals", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(entry),
  });
  if (!res.ok) throw new Error(`Log failed (${res.status})`);
  return res.json();
}

/* ---------- topbar ---------- */
function renderTopbar(active) {
  const links = [
    ["index.html", "Cases", "list", "queue"],
    ["case.html", "Case Copilot", "case", "clipboard"],
    ["log.html", "Approval Log", "log", "file"],
  ];
  const nav = links
    .map(([href, label, key, ic]) =>
      `<a href="${href}" class="${active === key ? "active" : ""}"${active === key ? ' aria-current="page"' : ""}>${icon(ic)}${label}</a>`)
    .join("");
  const opts = STAFF_IDS.map((id) => `<option ${id === getStaff() ? "selected" : ""}>${id}</option>`).join("");
  const bar = document.createElement("header");
  bar.className = "topbar";
  bar.innerHTML = `
    <div class="brand">
      <span class="mark" aria-hidden="true">${icon("plane")}</span>
      <span class="name">VisaConnect<small>Case Copilot</small></span>
    </div>
    <nav class="nav" aria-label="Primary">${nav}</nav>
    <div class="spacer"></div>
    <span class="hitl-note">${icon("spark")}AI drafts &amp; flags — a human approves</span>
    <div class="whoami">
      <label class="sr-only" for="staffSelect">Signed in as staff id</label>
      <span>Signed in as</span>
      <select id="staffSelect" title="Mock login">${opts}</select>
    </div>`;
  document.body.prepend(bar);
  $("#staffSelect").addEventListener("change", (e) => { setStaff(e.target.value); toast(`Signed in as ${e.target.value}`); });
}

/* ---------- hooks for grouping flags ---------- */
const FLAG_SEVERITY = {
  TRANSPORT_CONFLICT: "bad",
  STATUS_TIMESTAMP_CONFLICT: "bad",
  SLA_BREACH: "bad",
  AMBIGUOUS_CASE: "warn",
  MISSING_REQUIRED_FIELD: "warn",
  UNASSIGNED_OWNER: "warn",
  MISSING_DOCUMENT: "warn",
  UNRESPONDED_CONTACT: "warn",
  NEGATIVE_SENTIMENT: "warn",
};
function flagKind(type) { return FLAG_SEVERITY[type] || "neutral"; }

/* case status -> badge tone (kept off yellow; yellow means "AI wrote this") */
function statusKind(status) {
  const s = String(status || "").toLowerCase();
  if (!s) return "neutral";
  if (s.includes("approv")) return "good";
  if (s.includes("reject")) return "bad";
  if (s.includes("hold") || s.includes("review")) return "warn";
  if (s.includes("submit") || s.includes("progress")) return "info";
  return "neutral";
}
function statusBadge(status) {
  return status ? badge(status, statusKind(status)) : badge("no status", "neutral");
}

/* ---------- loading skeletons ---------- */
function skeletonRows(tbody, cols, rows = 8) {
  if (!tbody) return;
  tbody.innerHTML = Array.from({ length: rows }, () =>
    `<tr class="sk-row">${Array.from({ length: cols }, () =>
      '<td><div class="skeleton sk-line"></div></td>').join("")}</tr>`).join("");
}
