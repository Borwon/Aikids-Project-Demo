/* VisaConnect Case Copilot — airport pickup assist.
   A synthetic 2D terminal plan, a walkway graph, A* routing and a position dot.

   What is real here, and what is not:
   - The terminal plan, the gate, the baggage belt and the pickup point are
     ILLUSTRATIVE DEMO DATA. The dataset stores no terminal/gate/belt fields and
     this demo ships no airport floor plan, so the waypoints are derived from the
     booking's airport code and a hash of the case id. The panel says so on
     screen; nothing here should be read as a real airport layout.
   - The only real position a browser can supply is device GPS. It is
     outdoor-grade and unreliable inside a terminal, and it cannot be placed on
     an illustrative plan, so a fix is shown as coordinates plus an accuracy
     radius and the dot is snapped to the nearest walkway point — stated on
     screen. There is no indoor positioning in this demo.
   - Simulated movement is always labelled "simulated".
   - When the booking sources disagree the panel refuses to choose an airport,
     the same rule the rest of the app follows.
*/

/* One generic terminal plan, in a 0-100 x 0-99 user-unit space:
   gates along the top, an airside corridor, a baggage reclaim hall, an arrivals
   hall with exit doors, and the kerbside pickup lane outside. The rows are spaced
   so every room name and waypoint label has a clear band to sit in. */
const PK_PLAN = {
  nodes: {
    G1: [16, 12], G2: [30, 12], G3: [44, 12], G4: [58, 12], G5: [72, 12],
    C1: [16, 24], C2: [44, 24], C3: [72, 24],
    M1: [44, 34], M2: [44, 42],
    B1: [22, 50], B2: [44, 50], B3: [66, 50],
    H1: [22, 64], H2: [44, 64], H3: [66, 64],
    X1: [30, 74], X2: [44, 74], X3: [58, 74],
    P1: [22, 88], P2: [40, 88], P3: [56, 88], P4: [72, 88],
  },
  edges: [
    ["G1", "C1"], ["G2", "C1"], ["G2", "C2"], ["G3", "C2"], ["G4", "C2"],
    ["G4", "C3"], ["G5", "C3"], ["C1", "C2"], ["C2", "C3"],
    ["C2", "M1"], ["M1", "M2"],
    ["M2", "B1"], ["M2", "B2"], ["M2", "B3"],
    ["B1", "H1"], ["B2", "H2"], ["B3", "H3"],
    ["H1", "H2"], ["H2", "H3"],
    ["H1", "X1"], ["H2", "X1"], ["H2", "X2"], ["H3", "X3"],
    ["X1", "P1"], ["X1", "P2"], ["X2", "P2"], ["X2", "P3"], ["X3", "P3"], ["X3", "P4"],
  ],
  /* drawn behind the graph: the rooms the walkways run through.
     labelAt keeps the room name and the waypoint labels out of each other's way. */
  areas: [
    { x: 6, y: 7, w: 88, h: 10, cls: "gates" },
    { x: 6, y: 20, w: 88, h: 12, cls: "walk" },
    { x: 6, y: 40, w: 88, h: 20, cls: "baggage", label: "Baggage reclaim", labelAt: [8, 58.4] },
    { x: 6, y: 62, w: 88, h: 18, cls: "hall", label: "Arrivals hall · exits", labelAt: [8, 79.4] },
    { x: 6, y: 83, w: 88, h: 11, cls: "kerb" },
  ],
};

const PK_GATES = ["G1", "G2", "G3", "G4", "G5"];
const PK_EXITS = [["X1", "B1"], ["X2", "B2"], ["X3", "A1"]];
const PK_BELTS = [["B1", "7"], ["B2", "4"], ["B3", "11"]];
const PK_PICKUPS = [["P1", "A1"], ["P2", "B2"], ["P3", "B3"], ["P4", "C1"]];

/* 1 plan unit ~= 6 m at the illustrative scale used for the step distances */
const PK_UNIT_M = 6;

function pkHash(s) {
  let h = 2166136261;
  for (let i = 0; i < String(s).length; i++) {
    h ^= String(s).charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function pkDist(a, b) {
  const [ax, ay] = a, [bx, by] = b;
  return Math.hypot(ax - bx, ay - by);
}

/* Dijkstra over the walkway graph; the graph is tiny so this is plenty. */
function pkRoute(from, to) {
  if (!PK_PLAN.nodes[from] || !PK_PLAN.nodes[to]) return [];
  if (from === to) return [from];
  const adj = {};
  for (const [a, b] of PK_PLAN.edges) {
    (adj[a] = adj[a] || []).push(b);
    (adj[b] = adj[b] || []).push(a);
  }
  const dist = { [from]: 0 };
  const prev = {};
  const seen = new Set();
  while (true) {
    let cur = null, best = Infinity;
    for (const n of Object.keys(dist)) {
      if (!seen.has(n) && dist[n] < best) { best = dist[n]; cur = n; }
    }
    if (cur === null) return [];
    if (cur === to) break;
    seen.add(cur);
    for (const nb of adj[cur] || []) {
      const d = dist[cur] + pkDist(PK_PLAN.nodes[cur], PK_PLAN.nodes[nb]);
      if (d < (dist[nb] ?? Infinity)) { dist[nb] = d; prev[nb] = cur; }
    }
  }
  const path = [to];
  let cur = to;
  while (prev[cur] !== undefined) { cur = prev[cur]; path.unshift(cur); }
  return path;
}

/* joins legs into one coordinate list, without repeating the join waypoint */
function pkChain(legs) {
  const nodes = [];
  for (const leg of legs) {
    for (const n of leg) if (nodes[nodes.length - 1] !== n) nodes.push(n);
  }
  return nodes.map((n) => PK_PLAN.nodes[n]);
}

function pkNodeLen(nodes) {
  let total = 0;
  for (let i = 1; i < nodes.length; i++) {
    total += pkDist(PK_PLAN.nodes[nodes[i - 1]], PK_PLAN.nodes[nodes[i]]);
  }
  return total;
}

function pkCoords(nodes) {
  return nodes.map((n) => PK_PLAN.nodes[n]);
}

function pkPolyline(pts) {
  return pts.map(([x, y]) => `${x},${y}`).join(" ");
}

function pkMeters(units) {
  return Math.round((units * PK_UNIT_M) / 5) * 5;
}

/* the demo waypoints for one booking: derived, never read from the data.
   pkHash is unsigned, so every shift here must be unsigned too — a signed >> would
   turn half the hashes negative and index off the end of these tables. */
function pkWaypoints(caseObj) {
  const h = pkHash(caseObj.case_id);
  return {
    gate: PK_GATES[h % PK_GATES.length],
    exit: PK_EXITS[(h >>> 3) % PK_EXITS.length],
    belt: PK_BELTS[(h >>> 6) % PK_BELTS.length],
    pickup: PK_PICKUPS[(h >>> 9) % PK_PICKUPS.length],
  };
}

function pkSvg(wp, youRoute, afterRoute, custRoute, youStart) {
  const area = PK_PLAN.areas.map((a) => `
      <g class="pk-area ${a.cls}">
        <rect x="${a.x}" y="${a.y}" width="${a.w}" height="${a.h}" rx="2.5"></rect>
      </g>`).join("");

  /* room names are drawn last, above the routes, so a route never crosses a label */
  const room = PK_PLAN.areas.filter((a) => a.label).map((a) =>
    `<text class="pk-room" x="${a.labelAt[0]}" y="${a.labelAt[1]}">${esc(a.label)}</text>`).join("");

  const walk = PK_PLAN.edges.map(([a, b]) =>
    `<line class="pk-walk" x1="${PK_PLAN.nodes[a][0]}" y1="${PK_PLAN.nodes[a][1]}" x2="${PK_PLAN.nodes[b][0]}" y2="${PK_PLAN.nodes[b][1]}"></line>`).join("");

  const mark = (id, cls, text, dx = 0, dy = 0) => {
    const [x, y] = PK_PLAN.nodes[id];
    return `<g class="pk-mark ${cls}">
        <circle cx="${x}" cy="${y}" r="2.6"></circle>
        <text x="${x + dx}" y="${y + dy}">${esc(text)}</text>
      </g>`;
  };

  return `<svg class="pk-plan" viewBox="-2 -2 104 103" role="img"
      aria-label="Illustrative terminal plan showing the customer's route from the arrival gate to the baggage belt and exit, your route from the kerbside lane to the meeting point, and the pickup point outside.">
      ${area}
      <g class="pk-walks">${walk}</g>
      <polyline class="pk-route cust" points="${pkPolyline(custRoute)}"></polyline>
      <polyline class="pk-route after" points="${pkPolyline(afterRoute)}"></polyline>
      <polyline class="pk-route you" points="${pkPolyline(youRoute)}"></polyline>
      ${room}
      ${mark(wp.gate, "gate", "Gate " + wp.gate.slice(1), -1, 5.6)}
      ${mark(wp.belt[0], "belt", "Belt " + wp.belt[1], 3.4, 1)}
      ${mark(wp.exit[0], "exit", "Exit " + wp.exit[1], 3.4, 1)}
      <g class="pk-mark pickup"><circle cx="${PK_PLAN.nodes[wp.pickup[0]][0]}" cy="${PK_PLAN.nodes[wp.pickup[0]][1]}" r="2.6"></circle>
        <text x="${PK_PLAN.nodes[wp.pickup[0]][0]}" y="${PK_PLAN.nodes[wp.pickup[0]][1] + 6.4}" text-anchor="middle">Pickup ${esc(wp.pickup[1])}</text></g>
      <g class="pk-mark you"><circle cx="${PK_PLAN.nodes[youStart][0]}" cy="${PK_PLAN.nodes[youStart][1]}" r="2.6"></circle>
        <text x="${PK_PLAN.nodes[youStart][0]}" y="${PK_PLAN.nodes[youStart][1] - 4.6}" text-anchor="middle">you park here</text></g>
      <g id="pkYou" hidden>
        <circle class="pk-pulse" cx="0" cy="0" r="3"></circle>
        <circle class="pk-dot" cx="0" cy="0" r="2.6"></circle>
      </g>
    </svg>`;
}

/* ---------- the panel ---------- */

function mountPickup(caseObj, refs) {
  const booking = caseObj.transport || null;
  const wp = pkWaypoints(caseObj);

  if (booking && booking.conflict) {
    refs.map.innerHTML = `<div class="pk-blocked">
        <strong>Which airport is correct is unresolved.</strong>
        <p>The itinerary says <b>${esc(booking.itinerary_value || "—")}</b> while the internal note says
        <b>${esc(booking.internal_note_value || "—")}</b>, and the booking system says
        <b>${esc(booking.airport_code || "—")}</b>. This panel will not pick one, so no route is drawn.</p>
      </div>`;
    refs.steps.innerHTML = "";
    refs.note.innerHTML = "Confirm the airport with the customer first — the same rule the rest of this app follows.";
    refs.chip.textContent = "no route";
    refs.locBtn.disabled = true;
    refs.simBtn.disabled = true;
    return;
  }

  /* Where you arrive is derived, but it is always a kerbside point, and the one
     nearest the exit keeps your drawn route from doubling back on itself. It is
     kept distinct from the pickup point so the walk you see is "in to the exit,
     back out to the pickup", which is the walk a driver actually makes. */
  const kerbs = ["P1", "P2", "P3", "P4"].filter((k) => k !== wp.pickup[0]);
  let youStart = kerbs[0];
  let youBest = Infinity;
  for (const k of kerbs) {
    const len = pkNodeLen(pkRoute(k, wp.exit[0]));
    if (len < youBest) { youBest = len; youStart = k; }
  }

  const youNodes = pkRoute(youStart, wp.exit[0]);
  const afterNodes = pkRoute(wp.exit[0], wp.pickup[0]);
  const youRoute = pkCoords(youNodes);
  const afterRoute = pkCoords(afterNodes);
  const custRoute = pkChain([pkRoute(wp.gate, wp.belt[0]), pkRoute(wp.belt[0], wp.exit[0])]);
  const fullRoute = youRoute.concat(afterRoute.slice(1));

  refs.map.innerHTML = pkSvg(wp, youRoute, afterRoute, custRoute, youStart);

  const meetM = pkMeters(pkNodeLen(youNodes));
  const afterM = pkMeters(pkNodeLen(afterNodes));
  const insideM = pkMeters(pkNodeLen(pkRoute(wp.gate, wp.belt[0])) + pkNodeLen(pkRoute(wp.belt[0], wp.exit[0])));

  refs.steps.innerHTML = `
    <ol class="pk-steps">
      <li><span class="n you">1</span><span><span class="t">Meet the customer at Exit ${esc(wp.exit[1])}</span>
        <span class="d">They come out here with their bag. About ${meetM} m of walking from the kerb.</span></span></li>
      <li><span class="n you">2</span><span><span class="t">Pickup point ${esc(wp.pickup[1])} is right outside</span>
        <span class="d">Through the same doors and onto the kerbside lane — about ${afterM} m on from the exit.</span></span></li>
      <li><span class="n cust">i</span><span><span class="t">Baggage belt ${esc(wp.belt[1])} is inside</span>
        <span class="d">The customer collects their bag there on the way out — ${insideM} m of walking on their side.</span></span></li>
    </ol>`;

  refs.note.innerHTML = `Terminal, gate, belt and pickup point are <b>illustrative demo values</b> derived from
    the booking's airport code (${esc(booking.airport_code || "—")}). This demo has no airport floor plan, so the plan
    and the distances are indicative only.`;

  /* ---- position: real device GPS, or a labelled simulation ---- */
  let watchId = null;
  let simTimer = null;
  const you = refs.map.querySelector("#pkYou");
  const dot = you.querySelector(".pk-dot");
  const pulse = you.querySelector(".pk-pulse");

  function place(pt, label) {
    you.hidden = false;
    dot.setAttribute("cx", pt[0]); dot.setAttribute("cy", pt[1]);
    pulse.setAttribute("cx", pt[0]); pulse.setAttribute("cy", pt[1]);
    refs.chip.textContent = label;
    refs.chip.classList.toggle("is-live", /gps/i.test(label));
  }

  function stop() {
    if (watchId !== null && navigator.geolocation) navigator.geolocation.clearWatch(watchId);
    watchId = null;
    if (simTimer) clearInterval(simTimer);
    simTimer = null;
    refs.locBtn.disabled = false;
    refs.simBtn.disabled = false;
    refs.simBtn.textContent = "Simulate walk";
  }

  refs.locBtn.addEventListener("click", () => {
    if (watchId !== null) { stop(); refs.chip.textContent = "location off"; you.hidden = true; return; }
    if (!navigator.geolocation) { refs.chip.textContent = "no GPS in this browser"; return; }
    refs.chip.textContent = "asking for location…";
    /* A device fix cannot be placed on an illustrative plan without inventing a
       mapping, so the dot goes to the one place a fix does tell us something:
       the kerbside lane you would arrive at. That is stated, not implied. */
    const kerbNode = youStart;
    watchId = navigator.geolocation.watchPosition(
      (pos) => {
        const acc = Math.round(pos.coords.accuracy || 0);
        place(PK_PLAN.nodes[kerbNode], `device GPS ±${acc} m · at the kerb`);
        refs.note.innerHTML = `Device GPS fix: ${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)}
          (±${acc} m). GPS is outdoors-grade and unreliable inside a terminal, and this plan is illustrative, so the fix
          is not drawn to scale — the dot marks the kerbside pickup lane, not an indoor position.`;
      },
      (err) => { refs.chip.textContent = "location unavailable"; refs.note.textContent = "Location was refused or failed: " + err.message; },
      { enableHighAccuracy: true, maximumAge: 5000 }
    );
  });

  refs.simBtn.addEventListener("click", () => {
    if (simTimer) { stop(); return; }
    if (watchId !== null) { stop(); refs.chip.textContent = "location off"; }
    refs.simBtn.textContent = "Stop simulation";
    refs.simBtn.disabled = false;
    refs.locBtn.disabled = true;
    let i = 0;
    place(fullRoute[0], "simulated");
    simTimer = setInterval(() => {
      i += 1;
      if (i >= fullRoute.length) { stop(); refs.chip.textContent = "at pickup point " + wp.pickup[1]; return; }
      /* step along the leg so the dot moves between waypoints, not just on them */
      place(fullRoute[i], "simulated");
    }, 1100);
  });
}
