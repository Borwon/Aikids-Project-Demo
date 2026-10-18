/* VisaConnect Case Copilot -- shared frontend helpers.
   No framework, no CDN: everything renders offline once the stdlib server is up. */

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
  if (!t) { t = document.createElement("div"); t.id = "toast"; t.className = "toast"; document.body.appendChild(t); }
  t.textContent = msg;
  requestAnimationFrame(() => t.classList.add("show"));
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove("show"), 2600);
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
    ["index.html", "Case List", "list"],
    ["case.html", "Case Copilot", "case"],
    ["log.html", "Approval Log", "log"],
  ];
  const nav = links
    .map(([href, label, key]) => `<a href="${href}" class="${active === key ? "active" : ""}">${label}</a>`)
    .join("");
  const opts = STAFF_IDS.map((id) => `<option ${id === getStaff() ? "selected" : ""}>${id}</option>`).join("");
  const bar = document.createElement("header");
  bar.className = "topbar";
  bar.innerHTML = `
    <div class="brand"><span class="mark">VC</span><span>VisaConnect<br><small>Case Copilot</small></span></div>
    <nav class="nav">${nav}</nav>
    <div class="spacer"></div>
    <span class="hitl-note">AI flags &amp; drafts only — a human approves</span>
    <div class="whoami">Signed in as
      <select id="staffSelect" title="Mock login">${opts}</select>
    </div>`;
  document.body.prepend(bar);
  $("#staffSelect").addEventListener("change", (e) => { setStaff(e.target.value); toast(`Signed in as ${e.target.value}`); });
}

/* ---------- hooks for grouping flags ---------- */
const FLAG_SEVERITY = {
  TRANSPORT_CONFLICT: "bad",
  STATUS_TIMESTAMP_CONFLICT: "bad",
  AMBIGUOUS_CASE: "warn",
  MISSING_REQUIRED_FIELD: "warn",
  UNASSIGNED_OWNER: "warn",
  MISSING_DOCUMENT: "warn",
  SLA_BREACH: "bad",
  UNRESPONDED_CONTACT: "warn",
  NEGATIVE_SENTIMENT: "warn",
};
function flagKind(type) { return FLAG_SEVERITY[type] || "neutral"; }
