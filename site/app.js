/* Ground Truth site. Reads data/latest.json and data/stations/<id>.json (contract: docs/STACK.md). No build step. */
(() => {
  "use strict";

  const I18N = {
    en: {
      status: {
        ok:     { label: "Agrees with neighbours", short: "Agrees",        todo: "Sensor looks reliable: use this reading." },
        watch:  { label: "Worth a look",            short: "Worth a look", todo: "Uncertain: compare it with the 4 monitors around it before acting." },
        flag:   { label: "Doesn't add up",          short: "Doesn't add up", todo: "Flagged: use the median of its 4 neighbours instead." },
        nodata: { label: "Not enough data",          short: "No data",     todo: "Can't be checked right now: use the median of its 4 neighbours." },
      },
      checkLabel: { ok: "Passes", watch: "Worth a look", flag: "Doesn't add up", nodata: "No data" },
      findStation: "Find your station",
      findPlaceholder: "Find your station, e.g. Anand Vihar",
      filterPlaceholder: "Filter by name or area, e.g. Noida",
      langToggleLabel: "Switch to Hindi",
      langToggleText: "हिं",
    },
    hi: {
      status: {
        ok:     { label: "पड़ोसियों से मेल खाता है", short: "मेल खाता है",   todo: "सेंसर ठीक लगता है: यही रीडिंग इस्तेमाल करें।" },
        watch:  { label: "एक बार देखें",           short: "एक बार देखें",  todo: "पक्का नहीं: फ़ैसले से पहले आस-पास के 4 मॉनिटरों से तुलना करें।" },
        flag:   { label: "आँकड़े मेल नहीं खाते",     short: "मेल नहीं खाते", todo: "आँकड़े मेल नहीं खाते: इसके 4 पड़ोसियों का बीच वाला मान (माध्यिका) इस्तेमाल करें।" },
        nodata: { label: "पर्याप्त डेटा नहीं",      short: "डेटा नहीं",     todo: "अभी जाँच संभव नहीं: 4 पड़ोसियों का बीच वाला मान (माध्यिका) इस्तेमाल करें।" },
      },
      checkLabel: { ok: "पास", watch: "एक बार देखें", flag: "मेल नहीं खाता", nodata: "डेटा नहीं" },
      findStation: "अपना स्टेशन खोजें",
      findPlaceholder: "स्टेशन खोजें, जैसे आनंद विहार",
      filterPlaceholder: "नाम या क्षेत्र से फ़िल्टर करें, जैसे नोएडा",
      langToggleLabel: "Switch to English",
      langToggleText: "EN",
    },
  };

  // the language, the page dictionary and tr`...` live in i18n.js; choosing a language reloads the page in it
  const { lang, tr, t: tx, detail } = window.GT_I18N;
  const t = () => I18N[lang];

  const STATUS = new Proxy({}, { get: (_, k) => t().status[k] });
  const CHECK_LABEL = new Proxy({}, { get: (_, k) => t().checkLabel[k] });
  const ORDER = ["flag", "watch", "ok", "nodata"];
  const CHECKS = [
    ["physics", tx("Physics"), tx("Can this reading be real?")],
    ["neighbours", tx("Neighbours"), tx("Does it agree with the stations around it?")],
    ["history", tx("History"), tx("Has it suddenly changed?")],
  ];
  const PARAMS = {
    pm10: { name: tx("PM10 (all dust)"), unit: "%" },
    pm25: { name: tx("PM2.5 (fine dust)"), unit: "%" },
    no2: { name: tx("NO2 (traffic gas)"), unit: "%" },
    relativehumidity: { name: tx("Humidity"), unit: "pts" },
  };
  // which measure each check looks at, so a card can say exactly what raised it
  const CHECK_PARAM = { physics: () => tx("PM2.5 and PM10"), neighbours: () => "PM10", history: (c) => (c.param === "relativehumidity" ? tx("humidity") : "PM10") };
  const MICRO = tx("A real local source, such as a busy junction, road dust, construction or burning within a few hundred metres, can also push one monitor away from neighbours 5–12 km off. Here, the monitor may be right.");
  const PM25_STANDARD = 60; // India NAAQS, 24-hour mean, µg/m³
  // one line of plain guidance per CPCB AQI band, after CPCB's own health statements (draft: team review pending)
  const BAND_TODO = {
    Good: "Good for outdoor activity.",
    Satisfactory: "Fine for outdoor activity. People with asthma may notice it.",
    Moderate: "Children and people with asthma or heart disease should take it easy outdoors.",
    Poor: "Keep long or hard outdoor activity short, especially for children.",
    "Very poor": "Keep children's outdoor activity short. Hold assembly indoors.",
    Severe: "Keep children indoors and avoid outdoor exercise.",
  };
  // a monitor that has gone quiet: the scorer stops judging it and says since when (docs/STACK.md)
  const silent = (s) => s.detail != null;

  const $ = (s, el = document) => el.querySelector(s);
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = (v, d = 0) => (v == null ? "–" : Number(v).toFixed(d));
  const milestones = (window.__milestones = []);
  const mark = (name) => { milestones.push({ t: performance.now() / 1000, name }); document.body.dataset.milestone = name; };

  // shape + colour per state, so state never rests on colour alone
  function icon(status, size = 14) {
    const c = { ok: "var(--ok)", watch: "var(--watch)", flag: "var(--flag)", nodata: "var(--nodata)" }[status];
    const s = size;
    const body = {
      ok: `<circle cx="7" cy="7" r="5.5" fill="${c}" stroke="#fff" stroke-width="1.5"/><path d="M4.4 7.2l1.8 1.8 3.4-3.6" stroke="#fff" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`,
      watch: `<path d="M7 1.2 13 12.2H1z" fill="${c}" stroke="#fff" stroke-width="1.3" stroke-linejoin="round"/><path d="M7 5.2v3.3" stroke="#3a2600" stroke-width="1.4" stroke-linecap="round"/><circle cx="7" cy="10.3" r=".85" fill="#3a2600"/>`,
      flag: `<rect x="2.2" y="2.2" width="9.6" height="9.6" rx="1.5" transform="rotate(45 7 7)" fill="${c}" stroke="#fff" stroke-width="1.3"/><path d="M7 4.2v3.6" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/><circle cx="7" cy="9.9" r=".9" fill="#fff"/>`,
      nodata: `<circle cx="7" cy="7" r="5" fill="#fff" stroke="${c}" stroke-width="1.8" stroke-dasharray="2.4 1.8"/>`,
    }[status];
    return `<svg class="ico" width="${s}" height="${s}" viewBox="0 0 14 14" aria-hidden="true">${body}</svg>`;
  }
  const pill = (status, label = STATUS[status].label) => `<span class="pill ${status}">${icon(status, 12)}${label}</span>`;
  const todo = (status) => `<p class="todo ${status}">${STATUS[status].todo}</p>`;
  function raisedBy(s) {
    if (s.status === "ok" || s.status === "nodata") return "";
    const hits = CHECKS.filter(([k]) => s.checks[k].status === s.status).map(([k, name]) => `${name} (${CHECK_PARAM[k](s.checks[k])})`);
    return hits.length ? `<p class="raised">${tx("Raised by:")} <b>${hits.join(" + ")}</b></p>` : "";
  }
  const short = (name) => name.replace(/,\s*(New )?Delhi$/, "").replace(/\s+-\s+(DPCC|CPCB|IMD|HSPCB|UPPCB)\b.*$/, "");
  // in a list grouped by city, the city is already the heading; twins with one name get their OpenAQ id
  const listName = (s, all) => {
    const n = short(s.name).replace(/,\s*(Noida|Ghaziabad|Gurugram|Faridabad|Bahadurgarh|Manesar)(,\s*UP)?$/, "");
    return all.filter((o) => short(o.name) === short(s.name)).length > 1 ? `${n} · ${s.id}` : n;
  };

  let latest = null, byId = new Map(), chart = null, selected = null, param = "pm10";

  // ---------- data ----------
  async function getJSON(url) {
    const r = await fetch(url, { cache: "no-cache" });
    if (!r.ok) throw new Error(`${url}: ${r.status}`);
    return r.json();
  }

  async function boot() {
    document.querySelectorAll("[data-pill]").forEach((el) => { el.outerHTML = pill(el.dataset.pill); });
    try {
      latest = await getJSON("data/latest.json");
    } catch (e) {
      $("#fresh").textContent = tx("Data unavailable");
      $("#fresh").classList.add("stale");
      $("#panel").innerHTML = `<div class="empty"><h2>${tx("Data is updating")}</h2><p>${tx("We couldn't load the latest readings. Try again in a minute.")}</p><button class="btn ghost" data-reload>${tx("Try again")}</button></div>`;
      $("#panel").querySelector("[data-reload]").addEventListener("click", () => location.reload());
      $("#stats").querySelectorAll(".skel").forEach((el) => { el.classList.remove("skel"); el.textContent = "–"; });
      $("#chrome-live").textContent = tx("Offline");
      mark("error");
      return;
    }
    latest.stations.forEach((s) => byId.set(s.id, s));
    renderFresh();
    loadWeather();
    loadFires();
    setInterval(renderPulse, 30000);
    renderStats();
    renderMap();
    renderLegend();
    const example = pickExample();
    renderExample(example);
    renderStory(example);
    renderMeanings();
    renderCheckExamples();
    renderTicks();
    renderRoster();
    setupSearch();
    window.addEventListener("hashchange", fromHash);
    $("#close-cta")?.addEventListener("click", (e) => { e.preventDefault(); window.scrollTo({ top: 0, behavior: "smooth" }); setTimeout(() => $("#search").focus(), 500); });
    mark("loaded");
    if (new URLSearchParams(location.search).get("demo") === "1" || location.hash === "#tour") tour();
    else if (byId.has(Number(location.hash.slice(1)))) fromHash();
    else if (example) select(example.id, { quiet: true, spot: spotFor(example) }); // the map never opens empty
  }

  function fromHash() {
    const id = Number(location.hash.slice(1));
    if (byId.has(id)) select(id, { fly: true });
  }

  const ago = (min) => (min < 1 ? tx("just now") : min < 60 ? tr`${Math.round(min)} min ago` : min < 48 * 60 ? tr`${Math.round(min / 60)} h ago` : tr`${Math.round(min / 1440)} days ago`);

  function renderFresh() {
    const el = $("#fresh");
    const t = new Date(latest.data_through);
    const hours = (Date.now() - t.getTime()) / 36e5;
    const when = t.toLocaleString("en-IN", { timeZone: "Asia/Kolkata", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hour12: false });
    el.textContent = tr`Readings through ${when} IST`;
    el.title = `Generated ${latest.generated_at}`;
    el.classList.toggle("stale", hours > 3);
    const live = $("#chrome-live");
    if (live) live.textContent = tr`Readings through ${when}`;
    renderPulse();
  }

  // the weather: one line under the hero, and the wind for the 3D dust (data/weather.json, written hourly by the Lambda)
  let weather = null;
  async function loadWeather() {
    try { weather = await getJSON("data/weather.json"); } catch (e) { return; }
    const el = $("#weather");
    if (!el || !weather || !weather.line) return;
    el.textContent = detail(weather.line);
    el.title = `Wind ${fmt(weather.wind_kmh)} km/h from the ${weather.wind_from || "?"}` +
      (weather.boundary_layer_m != null ? `, mixing height ${fmt(weather.boundary_layer_m)} m` : "") + ` (${weather.source})`;
    // the arrow points where the wind blows to; weather.wind_from_deg is where it comes from
    if (weather.wind_from_deg != null) el.style.setProperty("--wind", `${(weather.wind_from_deg + 180) % 360}deg`);
    el.hidden = false;
    view?.setWind?.(weather.wind_from_deg, weather.wind_kmh);
  }

  // farm fires (data/fires.json, NASA FIRMS via the Lambda, only when a FIRMS key is configured): a line in the
  // hero, and embers on the 3D horizon in the fires' direction
  let firesDoc = null;
  async function loadFires() {
    try { firesDoc = await getJSON("data/fires.json"); } catch (e) { return; }
    const el = $("#fires");
    if (!el || !firesDoc || !firesDoc.line) return;
    el.textContent = detail(firesDoc.line);
    el.title = `${firesDoc.high_confidence ?? 0} at high confidence, about ${fmt(firesDoc.distance_km)} km away (${firesDoc.source})`;
    el.hidden = false;
    view?.setFires?.(firesDoc);
  }

  // is the hourly check itself running? from the time of its last run, ticking every 30 s
  function renderPulse() {
    const el = $("#pulse");
    const run = new Date(latest.generated_at);
    if (!el || isNaN(run)) return;
    const min = (Date.now() - run.getTime()) / 6e4;
    const live = min <= 75;
    el.className = `pulse ${live ? "on" : "off"}`;
    el.textContent = live ? tr`Live · checked ${ago(min)} · next check in ${Math.max(1, Math.round(60 - (min % 60)))} min` : tr`Paused · last check ${ago(min)}`;
    el.title = live ? "The check runs every hour on AWS" : "The hourly check hasn't run recently; the answers below are from its last run";
    el.hidden = false;
  }

  function renderStats() {
    const n = latest.stations.length;
    const count = (st) => latest.stations.filter((s) => s.status === st).length;
    const stats = $("#stats").children;
    const set = (i, v) => { const b = stats[i].querySelector("b"); b.classList.remove("skel"); b.textContent = v; };
    set(0, n);
    set(1, count("flag"));
    set(2, count("watch"));
    $("#hero-label").textContent = tr`Delhi + NCR · ${n} monitors · checked hourly`;
  }

  // the hero shows the product: the clearest current case, straight from the data
  function pickExample() {
    // the doubtful station whose reading differs most from its neighbours' right now
    const gap = (x) => Math.abs(Math.log((x.latest.pm25 + 1) / (x.neighbours_latest.pm25 + 1)));
    const cases = latest.stations
      .filter((x) => (x.status === "flag" || x.status === "watch") && x.latest?.pm25 != null && x.neighbours_latest?.pm25 != null)
      .sort((a, b) => ORDER.indexOf(a.status) - ORDER.indexOf(b.status) || gap(b) - gap(a));
    const best = cases.find((x) => gap(x) > Math.log(1.25));
    return best || cases[0] || latest.stations.find((x) => x.status === "flag") || latest.stations.find((x) => x.status === "watch") || null;
  }

  const spotFor = (s) => CHECKS.find(([k]) => s.checks[k].status === s.status)?.[0];
  const openStation = (id, spot) => { select(id, { fly: true, spot }); $("#live").scrollIntoView({ behavior: "smooth", block: "start" }); };

  function renderExample(s) {
    const el = $("#example");
    if (!s) { el.remove(); return; }
    const c = CHECKS.map(([k, name]) => [name, s.checks[k]]).find(([, v]) => v.status === s.status) || ["", { detail: "" }];
    el.innerHTML = `
      <span class="label">${tx("Right now, for example")}</span>
      <h3>${esc(short(s.name))}</h3>
      ${pill(s.status)}
      ${todo(s.status)}
      <div class="nums">${tr`This station <b>${fmt(s.latest?.pm25)}</b> µg/m³ PM2.5 · the 4 stations around it <b>${fmt(s.neighbours_latest?.pm25)}</b>`}</div>
      <button class="btn dark" type="button" data-open="${s.id}">${tx("See why")} <span class="arr">→</span></button>`;
    el.querySelector("[data-open]").addEventListener("click", () => openStation(s.id, spotFor(s)));
    el.hidden = false;
  }


  // ---------- the 10-second story, told with one real station ----------
  const mast = (h = 64) => `<svg width="${h * .75}" height="${h}" viewBox="0 0 48 64" aria-hidden="true"><path d="M24 62V18" stroke="#2b2c2f" stroke-width="2.5"/><path d="M24 62 14 64M24 62l10 2" stroke="#2b2c2f" stroke-width="2"/><rect x="11" y="18" width="26" height="20" rx="3" fill="#3a3b3e"/><path d="M14 25h20M14 30h20" stroke="#6b6c70" stroke-width="1.4"/><circle cx="24" cy="12" r="3" fill="#1f9d5c"/><circle cx="24" cy="12" r="6.5" fill="#1f9d5c" opacity=".18"/></svg>`;

  async function renderStory(s) {
    if (!s || s.latest?.pm25 == null) return; // the generic copy in the HTML stays
    let doc = null;
    try { doc = await getJSON(`data/stations/${s.id}.json`); } catch (e) { return; }
    const nbs = (doc.neighbours || []).map((i) => byId.get(i)).filter(Boolean);
    const name = esc(short(s.name));
    $("#step1-art").innerHTML = `<div class="reading">${mast(58)}<div class="big">${fmt(s.latest.pm25)}</div><div class="unit">µg/m³ PM2.5</div><div class="who">${name}</div></div>`;
    $("#step1-title").textContent = tr`${short(s.name)} says ${fmt(s.latest.pm25)}`;
    $("#step1-text").textContent = tx("That's its PM2.5 reading for the latest hour. On its own, there's no way to tell whether it's right.");
    const around = s.neighbours_latest?.pm25;
    $("#step2-art").innerHTML = `<div class="nbgrid">${nbs.map((n) => `<div class="nb"><b>${fmt(n.latest?.pm25)}</b><span>${esc(short(n.name))}</span></div>`).join("")}<div class="nbmid">${tx("middle value")} <b>${fmt(around)}</b> µg/m³</div></div>`;
    $("#step2-title").textContent = tr`Its four neighbours say ${fmt(around)}`;
    $("#step2-text").textContent = tx("We take the middle value of the four nearest monitors, within 12 km. One odd neighbour can't drag it.");
    const use = s.status === "ok" ? s.latest.pm25 : around;
    $("#step3-art").innerHTML = `<div class="verdict">${pill(s.status)}<div class="use">${tx("For today, use")}<b>${fmt(use)}</b>µg/m³ PM2.5</div></div>`;
    $("#step3-title").textContent = s.status === "ok" ? tx("It adds up, so use it") : tr`${STATUS[s.status].label}: use ${fmt(around)}`;
    $("#step3-text").textContent = tx("Before answering, we also check the reading against physics and against the monitor's own last three weeks. Every answer shows its evidence.");
  }

  function renderMeanings() {
    const groups = {};
    latest.stations.forEach((s) => (groups[s.status] = groups[s.status] || []).push(s));
    const copy = {
      ok: [tx("Its numbers add up against physics, its neighbours and its own past."), tx("Use its reading as it is.")],
      watch: [tx("Something about it is unusual, but not clearly wrong."), tx("Compare its reading with what its neighbours read before acting on it.")],
      flag: [tx("Its numbers don't add up: impossible values, or far out of line with its neighbours or its past."), tx("Use what the four monitors around it read instead.")],
      nodata: [tx("We can't check it right now: too few recent readings from it or its neighbours to run the checks."), tx("Use what the four monitors around it read.")],
    };
    $("#meanings").innerHTML = ["ok", "watch", "flag", "nodata"].map((st) => {
      const list = (groups[st] || []).slice().sort((a, b) => a.name.localeCompare(b.name));
      const shown = list.slice(0, st === "ok" ? 4 : 6);
      return `<article class="meaning">
        <div class="head">${icon(st, 30)}<h3>${STATUS[st].label}</h3></div>
        <dl><dt>${tx("What it means")}</dt><dd>${copy[st][0]}</dd><dt>${tx("What to do")}</dt><dd>${copy[st][1]}</dd>${st === "nodata" ? `<dt>${tx("Why it happens")}</dt><dd>${tx("Almost always, the monitor stopped sending readings to the public feed (CPCB, through OpenAQ): a power cut, a network outage or maintenance. It isn't a fault in our checks. The <i>Live · checked … ago</i> pill at the top shows that our own hourly run is working.")}</dd>` : ""}</dl>
        <div class="now-count"><b>${list.length}</b><span>${tx(list.length === 1 ? "monitor right now" : "monitors right now")}${list.length > shown.length ? tx(", for example:") : list.length ? ":" : ""}</span></div>
        <div class="chips">${shown.map((s) => `<button type="button" data-open="${s.id}">${esc(short(s.name))}</button>`).join("")}</div>
      </article>`;
    }).join("");
    $("#meanings").querySelectorAll("[data-open]").forEach((b) => b.addEventListener("click", () => { const s = byId.get(Number(b.dataset.open)); openStation(s.id, spotFor(s)); }));
  }

  function svgLine(values, { w = 320, h = 150, band = null, zero = true } = {}) {
    const pts = values.map((v, i) => [i, v]).filter(([, v]) => v != null);
    if (pts.length < 2) return "";
    const ys = pts.map(([, v]) => v).concat(zero ? [0] : []);
    const lo = Math.min(...ys), hi = Math.max(...ys), pad = (hi - lo) * 0.15 || 1;
    const X = (i) => 16 + (i / (values.length - 1)) * (w - 32), Y = (v) => h - 18 - ((v - (lo - pad)) / (hi - lo + 2 * pad)) * (h - 36);
    const d = pts.map(([i, v], k) => `${k ? "L" : "M"}${X(i).toFixed(1)} ${Y(v).toFixed(1)}`).join("");
    const b = band ? `<rect x="${X(band[0] - .5)}" y="10" width="${X(band[1] + .5) - X(band[0] - .5)}" height="${h - 28}" fill="rgba(242,166,12,.12)"/><text x="${(X(band[0]) + X(band[1])) / 2}" y="${h - 4}" text-anchor="middle" font-family="Geist Mono" font-size="10" fill="#8b8d93">11:00-17:00</text>` : "";
    const z = zero ? `<path d="M16 ${Y(0)}H${w - 16}" stroke="#b4b5ba" stroke-dasharray="3 3"/><text x="${w - 16}" y="${Y(0) - 5}" text-anchor="end" font-family="Geist Mono" font-size="10" fill="#8b8d93">${tx("same as neighbours")}</text>` : "";
    return `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true">${b}${z}<path d="${d}" fill="none" stroke="#08090a" stroke-width="2" stroke-linejoin="round"/></svg>`;
  }

  function svgDaily(values, recent = 7, { w = 320, h = 150 } = {}) {
    const vals = values.map((v) => (v == null ? null : v));
    const nums = vals.filter((v) => v != null);
    if (nums.length < 5) return "";
    const lo = Math.min(0, ...nums), hi = Math.max(0, ...nums), span = hi - lo || 1;
    const bw = (w - 32) / vals.length, Y = (v) => 14 + ((hi - v) / span) * (h - 40);
    const bars = vals.map((v, i) => {
      if (v == null) return "";
      const y0 = Y(0), y1 = Y(v), r = i >= vals.length - recent;
      return `<rect x="${(16 + i * bw + 1).toFixed(1)}" y="${Math.min(y0, y1).toFixed(1)}" width="${(bw - 2).toFixed(1)}" height="${Math.max(1, Math.abs(y1 - y0)).toFixed(1)}" rx="1.5" fill="${r ? "#08090a" : "#c9cace"}"/>`;
    }).join("");
    return `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true"><path d="M16 ${Y(0)}H${w - 16}" stroke="#d6d6d9"/>${bars}<text x="16" y="${h - 6}" font-family="Geist Mono" font-size="10" fill="#8b8d93">${tx("3 weeks before")}</text><text x="${w - 16}" y="${h - 6}" text-anchor="end" font-family="Geist Mono" font-size="10" fill="#08090a">${tx("last 7 days")}</text></svg>`;
  }

  async function renderCheckExamples() {
    const worst = (k, key) => latest.stations.filter((s) => s.checks[k].status === "flag" || s.checks[k].status === "watch")
      .sort((a, b) => Math.abs(b.checks[k][key] ?? 0) - Math.abs(a.checks[k][key] ?? 0))[0];
    const link = (s) => `<button type="button" data-open="${s.id}" data-spot="${s._spot}">${esc(short(s.name))}</button>`;

    // physics: what an impossible reading looks like, and who does it now
    $("#ex-physics").innerHTML = `<svg viewBox="0 0 320 150" aria-hidden="true"><text x="96" y="140" text-anchor="middle" font-family="Geist Mono" font-size="11" fill="#4f5156">${tx("PM10 (all dust)")}</text><text x="224" y="140" text-anchor="middle" font-family="Geist Mono" font-size="11" fill="#4f5156">${tx("PM2.5 (fine dust)")}</text><rect x="66" y="58" width="60" height="66" rx="5" fill="#c9cace"/><rect x="194" y="22" width="60" height="102" rx="5" fill="#d03b3b" opacity=".85"/><path d="M60 58h200" stroke="#08090a" stroke-dasharray="4 4"/><text x="96" y="50" text-anchor="middle" font-family="Geist Mono" font-size="10.5" fill="#4f5156">${tx("the limit")}</text><text x="224" y="80" text-anchor="middle" font-family="Geist Mono" font-size="11" fill="#ffffff">${tx("impossible")}</text></svg>`;
    const p = worst("physics", "fail_pct");
    if (p) { p._spot = "physics"; $("#ex-physics-case").innerHTML = tr`Right now: ${link(p)} reports impossible values in ${p.checks.physics.fail_pct}% of last week's hours.`; }

    const n = worst("neighbours", "z");
    if (n) {
      n._spot = "neighbours";
      try {
        const doc = await getJSON(`data/stations/${n.id}.json`);
        const pct = (doc.hour_profile_7d?.pm10 || []).map((g) => (g == null ? null : (Math.exp(g) - 1) * 100));
        $("#ex-neighbours").innerHTML = svgLine(pct, { band: [11, 16] });
      } catch (e) { /* the card still reads without the picture */ }
      $("#ex-neighbours-case").innerHTML = tr`Right now: ${link(n)}. ${esc(detail(n.checks.neighbours.detail))}`;
    }

    const h = worst("history", "z");
    if (h) {
      h._spot = "history";
      try {
        const doc = await getJSON(`data/stations/${h.id}.json`);
        const key = `d_${h.checks.history.param}`;
        $("#ex-history").innerHTML = svgDaily(doc.daily.map((r) => r[key]));
      } catch (e) { /* the card still reads without the picture */ }
      $("#ex-history-case").innerHTML = tr`Right now: ${link(h)}. ${esc(detail(h.checks.history.detail))}`;
    }
    document.querySelectorAll(".c3-case [data-open]").forEach((b) => b.addEventListener("click", () => openStation(Number(b.dataset.open), b.dataset.spot)));
  }

  function renderTicks() {
    const tick = `<svg viewBox="0 0 14 14" aria-hidden="true"><path d="M3.5 7.4l2.3 2.3 4.7-5" stroke="#0a6b0a" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
    $("#ticks").innerHTML = Array.from({ length: 30 }, (_, i) => `<i style="animation-delay:${(i * 0.03).toFixed(2)}s">${tick}</i>`).join("");
  }

  // ---------- 3D map (scene3d.js, three.js): our own Delhi in fog ----------
  let view = null, immersive = false;
  const mapWindow = () => $("#map").closest(".window"); // not the first .window: the tanker illustration comes before it
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const reading = (s) => (silent(s) ? null : s.latest?.pm25 ?? s.neighbours_latest?.pm25 ?? null);

  function markerEl(s) {
    const el = document.createElement("button");
    el.type = "button";
    el.className = `gt-marker${s.region === "NCR" ? " ncr" : ""}`;
    el.dataset.name = `${short(s.name)} · ${STATUS[s.status].label}`;
    el.setAttribute("aria-label", `${s.name}: ${STATUS[s.status].label}`);
    el.innerHTML = icon(s.status, 22);
    el.addEventListener("click", (e) => { e.stopPropagation(); select(s.id, { fly: true }); });
    return el;
  }

  // ---------- list view ----------
  let listSortCol = "status", listSortAsc = true;

  function renderListView() {
    const tbody = $("#monitor-table-body");
    if (!tbody || !latest) return;
    const rows = [...latest.stations].sort((a, b) => {
      let av, bv;
      if (listSortCol === "name") { av = short(a.name); bv = short(b.name); }
      else if (listSortCol === "area") { av = a._area || ""; bv = b._area || ""; }
      else if (listSortCol === "status") { av = ORDER.indexOf(a.status); bv = ORDER.indexOf(b.status); }
      else if (listSortCol === "pm25") { av = a.latest?.pm25 ?? -1; bv = b.latest?.pm25 ?? -1; }
      else if (listSortCol === "nb_pm25") { av = a.neighbours_latest?.pm25 ?? -1; bv = b.neighbours_latest?.pm25 ?? -1; }
      else { av = 0; bv = 0; }
      return listSortAsc ? (av < bv ? -1 : av > bv ? 1 : 0) : (av < bv ? 1 : av > bv ? -1 : 0);
    });
    tbody.innerHTML = rows.map((s) => `
      <tr>
        <td><button type="button" class="list-open" data-open="${s.id}">${esc(short(s.name))}</button></td>
        <td>${esc(s._area || "")}</td>
        <td>${pill(s.status, STATUS[s.status].short)}</td>
        <td class="mono">${fmt(s.latest?.pm25, 0)}</td>
        <td class="mono">${fmt(s.neighbours_latest?.pm25, 0)}</td>
      </tr>`).join("");
    tbody.querySelectorAll(".list-open").forEach((b) => {
      b.addEventListener("click", () => {
        const id = Number(b.dataset.open);
        toggleListView(false);
        select(id, { fly: true });
        $("#live").scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
  }

  function setupSortButtons() {
    document.querySelectorAll(".sort-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const col = btn.dataset.col;
        if (listSortCol === col) { listSortAsc = !listSortAsc; }
        else { listSortCol = col; listSortAsc = true; }
        document.querySelectorAll(".sort-btn").forEach((b) => {
          b.setAttribute("aria-sort", b.dataset.col === listSortCol ? (listSortAsc ? "ascending" : "descending") : "none");
        });
        renderListView();
      });
    });
  }

  function toggleListView(show) {
    const listEl = $("#list-view"), mapEl = $("#map"), btn = $("#list-toggle");
    if (show === undefined) show = listEl?.hidden;
    if (listEl) listEl.hidden = !show;
    if (mapEl) mapEl.hidden = show;
    if (btn) {
      btn.setAttribute("aria-pressed", String(show));
      btn.textContent = tx(show ? "Map view" : "List view");
    }
    if (show) renderListView();
  }

  function renderMap() {
    const start = async () => {
      try {
        view = await window.GT3D.init($("#map"), {
          stations: latest.stations, reading, makeMarker: markerEl,
          onPick: (id) => select(id, { fly: true }),
          onBackgroundClick: () => { if (!immersive) enterImmersive(); },
        });
      } catch (e) {
        $("#map").innerHTML = "";
        return renderFlat();
      }
      if (selected != null) view.select(selected);
      mark("map:ready");
    };
    let webgl = false;
    try { webgl = !!document.createElement("canvas").getContext("webgl2"); } catch (e) { /* stays false */ }
    if (!webgl) renderFlat();
    else if (window.GT3D) start(); else window.addEventListener("gt3d:loaded", start, { once: true });
    $("#enter3d").addEventListener("click", (e) => { e.stopPropagation(); enterImmersive(); });
    $("#list-toggle")?.addEventListener("click", () => toggleListView());
    setupSortButtons();
    $("#exit3d").addEventListener("click", exitImmersive);
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && immersive) exitImmersive(); });
  }

  // without WebGL: Delhi's wards as a flat SVG, with the same markers opening the same panel
  async function renderFlat() {
    const map = $("#map");
    map.classList.add("flat");
    $("#enter3d").hidden = true;
    let wards = { features: [] };
    try { wards = await getJSON("geo/delhi_wards.json"); } catch (e) { /* the markers still work on their own */ }
    const k = Math.cos((28.63 * Math.PI) / 180), P = ([lon, lat]) => [lon * k, -lat]; // equirectangular at Delhi
    const rings = wards.features.flatMap((f) => (f.geometry.type === "Polygon" ? [f.geometry.coordinates[0]] : f.geometry.coordinates.map((c) => c[0])));
    const pts = rings.flat().map(P).concat(latest.stations.map((s) => P([s.lon, s.lat])));
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
    const pad = 0.02, x0 = Math.min(...xs) - pad, y0 = Math.min(...ys) - pad, w = Math.max(...xs) + pad - x0, h = Math.max(...ys) + pad - y0;
    const d = rings.map((r) => "M" + r.map((c) => P(c).map((v, i) => (v - (i ? y0 : x0)).toFixed(4)).join(" ")).join("L") + "Z").join("");
    map.innerHTML = `<div class="flatmap" style="aspect-ratio:${w.toFixed(4)}/${h.toFixed(4)}"><svg viewBox="0 0 ${w.toFixed(4)} ${h.toFixed(4)}" aria-hidden="true"><path d="${d}"/></svg></div><p class="flatnote">A flat map, because this browser can't show the 3D view.</p>`;
    const box = $(".flatmap", map), marks = new Map();
    for (const s of latest.stations) {
      const [x, y] = P([s.lon, s.lat]), el = markerEl(s);
      el.style.left = `${((x - x0) / w) * 100}%`; el.style.top = `${((y - y0) / h) * 100}%`;
      box.appendChild(el); marks.set(s.id, el);
    }
    view = { select: (id) => marks.forEach((el, k2) => el.classList.toggle("sel", k2 === id)), focus() {}, setImmersive() {}, setWind() {}, setFires() {} };
    if (selected != null) view.select(selected);
    mark("map:ready");
  }

  function enterImmersive() {
    if (immersive) return;
    immersive = true;
    mapWindow().classList.add("immersive");
    document.documentElement.classList.add("lock");
    $("#exit3d").hidden = false; $("#enter3d").hidden = true;
    view?.setImmersive(true, { autoRotate: !reduced });
    mark("map:3d");
  }

  function exitImmersive() {
    immersive = false;
    mapWindow().classList.remove("immersive");
    document.documentElement.classList.remove("lock");
    $("#exit3d").hidden = true; $("#enter3d").hidden = false;
    view?.setImmersive(false);
  }

  function renderLegend() {
    const count = (st) => latest.stations.filter((s) => s.status === st).length;
    $("#legend").innerHTML = ORDER.map((st) => `<span>${icon(st, 14)}${STATUS[st].label} <span class="count">${count(st)}</span></span>`).join("");
  }

  // ---------- station panel ----------
  async function select(id, { fly = false, spot = null, quiet = false } = {}) {
    const s = byId.get(id);
    if (!s) return;
    selected = id;
    view?.select(id);
    if (fly) view?.focus(id);
    if (!quiet && location.hash !== `#${id}`) history.replaceState(null, "", `${location.search}#${id}`);

    const panel = $("#panel");
    panel.innerHTML = panelHTML(s, null);
    let doc = null;
    try { doc = await getJSON(`data/stations/${id}.json`); } catch (e) { /* the chart says so */ }
    if (selected !== id) return;
    smokeDoc = doc;
    panel.innerHTML = panelHTML(s, doc);
    if (spot) spotCheck(spot);
    drawChart(doc);
    drawEvidence(doc, s);
    panel.querySelectorAll("[data-goto]").forEach((b) => b.addEventListener("click", () => select(Number(b.dataset.goto), { fly: true })));
    panel.querySelector("#param")?.addEventListener("change", (e) => { param = e.target.value; drawChart(doc); });
    panel.querySelector("#as-table")?.addEventListener("click", () => toggleTable(doc));
    const h2 = panel.querySelector("h2");
    if (h2 && !quiet) { h2.setAttribute("tabindex", "-1"); h2.focus({ preventScroll: true }); }
    panel.querySelector("#share-btn")?.addEventListener("click", function () {
      const url = `${location.origin}${location.pathname}${location.search}#${id}`;
      if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(() => { this.textContent = `✓ ${tx("Copied!")}`; setTimeout(() => { this.textContent = `🔗 ${tx("Copy link")}`; }, 2000); });
      } else {
        prompt(tx("Copy this link:"), url);
      }
    });
    mark(`station:${id}`);
  }

  function adviceHTML(s) {
    const mine = s.latest?.pm25, around = s.neighbours_latest?.pm25;
    const aroundTxt = around == null ? "" : tr` The four nearest stations read <b class="mono">${fmt(around)} µg/m³</b> PM2.5 right now.`;
    if (silent(s)) return `${bandHTML(s)}<div class="advice nodata">${tr`${esc(detail(s.detail))} Its last answers are below, but they no longer describe the air now. Use what the stations around it read.${aroundTxt}`}</div>`;
    const text = {
      ok: tx("This station agrees with the stations around it. Its reading is a fair guide for this area."),
      watch: tr`Something about this station is unusual. Before acting on its reading, compare it with the stations around it.${aroundTxt}`,
      flag: around == null
        ? tx("This station's numbers don't add up, and its neighbours have no reading right now either. Treat today's number with care.")
        : tr`This station's numbers don't add up. For decisions today, use what the stations around it read.${aroundTxt}`,
      nodata: tr`There isn't enough recent data to check this station.${aroundTxt}`,
    }[s.status];
    // a big gap right now is worth saying even when the weekly checks pass
    let gapTxt = "";
    if (mine != null && around != null && Math.max(mine, around) >= 15) {
      const r = (mine + 1) / (around + 1);
      if (r > 1.5 || r < 1 / 1.5) gapTxt = tr` Right now, though, it reads <b>${tx(r > 1 ? "well above" : "well below")}</b> the stations around it (${fmt(mine)} against ${fmt(around)} µg/m³).` + (r > 1 ? ` <span class="micro">${MICRO}</span>` : "");
    }
    return `${bandHTML(s)}<div class="advice ${s.status}">${text}${gapTxt}${smokeHTML(s)}</div>`;
  }

  // the last 6 hours against the 24 before, for this station and the median of its neighbours (data/stations/<id>.json)
  function roseTogether(doc) {
    const r = doc?.recent_48h;
    if (!r || !r.pm25 || r.pm25.length < 30) return null;
    const mean = (xs) => { const v = xs.filter((x) => x != null); return v.length >= Math.ceil(xs.length / 2) ? v.reduce((a, b) => a + b, 0) / v.length : null; };
    const median = (xs) => { const v = xs.filter((x) => x != null).sort((a, b) => a - b); return v.length ? v[Math.floor(v.length / 2)] : null; };
    const nb = Object.values(r.neighbours_pm25 || {});
    if (nb.length < 2) return null;
    const nbSeries = r.hours.map((_, i) => median(nb.map((a) => a[i])));
    const split = r.hours.length - 6;
    const mine = [mean(r.pm25.slice(split - 24, split)), mean(r.pm25.slice(split))];
    const theirs = [mean(nbSeries.slice(split - 24, split)), mean(nbSeries.slice(split))];
    if (mine.includes(null) || theirs.includes(null) || mine[0] < 10 || theirs[0] < 10) return null;
    const up = (a) => (a[1] + 1) / (a[0] + 1);
    return up(mine) >= 1.5 && up(theirs) >= 1.5 ? { mine: up(mine), theirs: up(theirs) } : null;
  }
  let smokeDoc = null;
  function smokeHTML(s) {
    const rose = roseTogether(smokeDoc);
    if (!rose) return "";
    const fireTxt = firesDoc && firesDoc.count ? ` ${esc(detail(firesDoc.line))}` : "";
    return `<span class="smoke">${tr`The whole area rose together in the last few hours (this station ${Math.round((rose.mine - 1) * 100)}%, its neighbours ${Math.round((rose.theirs - 1) * 100)}%), which is what smoke does, not what a broken monitor does.`}${fireTxt}</span>`;
  }

  // how bad the air is, in CPCB's words, from the reading you can trust: its own if it agrees, else its neighbours'
  function bandHTML(s) {
    const own = s.status === "ok";
    const b = own ? s.band : s.neighbours_band;
    if (!b) return "";
    return `<div class="aqi"><span class="label">${tr`Air quality, 24-hour average · ${tx(own ? "this monitor" : "from the 4 monitors around it")}`}</span><b>${esc(window.GT_I18N.band(b))}</b><p>${window.GT_I18N.bandTodo(b, BAND_TODO[b])}</p></div>`;
  }

  function lastHTML(s) {
    if (!s.last_reading) return `<div class="last off">${tx("No reading in the last 4 weeks.")}</div>`;
    const t = new Date(s.last_reading);
    const when = t.toLocaleString("en-IN", { timeZone: "Asia/Kolkata", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hour12: false });
    return `<div class="last${silent(s) ? " off" : ""}">${tr`Last reading ${when} IST, ${ago((Date.now() - t.getTime()) / 6e4)}`}</div>`;
  }

  function panelHTML(s, doc) {
    const nb = doc?.neighbours?.map((i) => byId.get(i)).filter(Boolean) || [];
    const checks = CHECKS.map(([k, name, q]) => {
      const c = s.checks[k];
      const note = k === "neighbours" && (c.status === "watch" || c.status === "flag") ? `<p class="micro">${tx("Note:")} ${MICRO}</p>` : "";
      return `<li class="check" data-check="${k}"><div><h3>${name} <span class="param">${CHECK_PARAM[k](c)}</span></h3><div class="q">${q}</div></div>${pill(c.status, CHECK_LABEL[c.status])}<p>${esc(detail(c.detail))}</p>${note}</li>`;
    }).join("");
    const opts = Object.entries(PARAMS).map(([k, p]) => `<option value="${k}"${k === param ? " selected" : ""}>${p.name}</option>`).join("");
    return `
      <span class="label">${s.region === "NCR" ? "NCR" : tx("Delhi")} · ${tr`OpenAQ location ${s.id}`}</span>
      <h2>${esc(short(s.name))}</h2>
      <div class="meta">${pill(s.status)}<button class="share-btn" id="share-btn" type="button" aria-label="${tx("Copy link to this monitor")}" title="${tx("Copy link")}">🔗 ${tx("Copy link")}</button></div>
      ${todo(s.status)}
      ${raisedBy(s)}
      <div class="now">
        <div><small>${tx("This station, PM2.5 now")}</small><b>${fmt(s.latest?.pm25)}<small> µg/m³</small></b></div>
        <div><small>${tx("4 nearest stations, PM2.5 now")}</small><b>${fmt(s.neighbours_latest?.pm25)}<small> µg/m³</small></b></div>
      </div>
      ${lastHTML(s)}
      <div class="std">${tr`India's 24-hour PM2.5 standard is ${PM25_STANDARD} µg/m³.`}</div>
      ${adviceHTML(s)}
      <ul class="checks">${checks}</ul>
      <div class="chartbox">
        <div style="display:flex;justify-content:space-between;gap:12px;align-items:baseline;flex-wrap:wrap">
          <div><h3>${tx("Hour by hour, against its neighbours")}</h3><p class="csub">${tx("Above zero: this station reads higher than the 4 nearest stations at that hour.")}</p></div>
          <label class="sr-only" for="param">${tx("Measure")}</label>
          <select id="param">${opts}</select>
        </div>
        <div class="chartwrap">${doc ? `<canvas id="chart" role="img" aria-label="Hour-of-day gap against neighbours"></canvas>` : `<div class="empty" style="min-height:220px"><p>${doc === null ? tx("Loading the chart…") : ""}</p></div>`}</div>
        <div class="chartlegend"><span><i style="background:var(--series-7d)"></i>${tx("Last 7 days")}</span><span><i style="background:var(--series-28d)"></i>${tx("Last 28 days")}</span><span><i class="band"></i>11:00-17:00</span><button class="linkish" id="as-table" type="button">${tx("Show as table")}</button></div>
        <div id="tablebox"></div>
      </div>
      ${doc ? `<div class="chartbox" id="evidence-box"><h3>${tx("Last 48 hours: this station vs neighbours")}</h3><p class="csub">${tr`PM2.5 µg/m³. Neighbour band is the range of the ${(doc.neighbours || []).length} nearest stations.`}</p><div class="chartwrap"><canvas id="evidence-chart" role="img" aria-label="PM2.5 last 48 hours"></canvas></div></div>` : ""}
      ${nb.length ? `<div class="nbs"><span class="label">${tx("Compared with")}</span>${nb.map((n) => `<button data-goto="${n.id}" type="button">${icon(n.status, 11)}${esc(short(n.name))}</button>`).join("")}</div>` : ""}
    `;
  }

  function series(doc, key) {
    const raw = doc?.[key]?.[param] || [];
    return raw.map((g) => (g == null ? null : PARAMS[param].unit === "%" ? (Math.exp(g) - 1) * 100 : g));
  }

  const bandPlugin = {
    id: "band",
    beforeDatasetsDraw(c) {
      const { ctx, chartArea: a, scales: { x, y } } = c;
      ctx.save();
      ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--band");
      const x0 = x.getPixelForValue(11) - (x.getPixelForValue(1) - x.getPixelForValue(0)) / 2;
      const x1 = x.getPixelForValue(16) + (x.getPixelForValue(1) - x.getPixelForValue(0)) / 2;
      ctx.fillRect(x0, a.top, x1 - x0, a.bottom - a.top);
      ctx.strokeStyle = "#b4b5ba"; ctx.lineWidth = 1; ctx.setLineDash([3, 3]);
      const z = y.getPixelForValue(0);
      if (z >= a.top && z <= a.bottom) { ctx.beginPath(); ctx.moveTo(a.left, z); ctx.lineTo(a.right, z); ctx.stroke(); }
      ctx.restore();
    },
  };

  function drawChart(doc) {
    const canvas = $("#chart");
    if (chart) { chart.destroy(); chart = null; }
    if (!canvas || !doc) return;
    const css = getComputedStyle(document.documentElement);
    const unit = PARAMS[param].unit;
    chart = new Chart(canvas, {
      type: "line",
      data: {
        labels: [...Array(24).keys()],
        datasets: [
          { label: tx("Last 28 days"), data: series(doc, "hour_profile"), borderColor: css.getPropertyValue("--series-28d").trim(), borderWidth: 2, pointRadius: 0, cubicInterpolationMode: "monotone", spanGaps: true },
          { label: tx("Last 7 days"), data: series(doc, "hour_profile_7d"), borderColor: css.getPropertyValue("--series-7d").trim(), borderWidth: 2, pointRadius: 0, pointHoverRadius: 5, cubicInterpolationMode: "monotone", spanGaps: true },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false, animation: matchMedia("(prefers-reduced-motion: reduce)").matches ? false : { duration: 500 },
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#ffffff", borderColor: "#d6d6d9", borderWidth: 1, titleColor: "#08090a", bodyColor: "#4f5156", titleFont: { family: "Geist Mono", size: 12 }, bodyFont: { family: "Geist", size: 12.5 }, padding: 10,
            callbacks: {
              title: (items) => `${String(items[0].label).padStart(2, "0")}:00 IST`,
              label: (it) => ` ${it.dataset.label}: ${it.raw == null ? tx("no data") : `${it.raw > 0 ? "+" : ""}${it.raw.toFixed(unit === "%" ? 0 : 1)}${unit === "%" ? "%" : " pts"}`}`,
            },
          },
        },
        scales: {
          x: { grid: { display: false }, ticks: { font: { family: "Geist Mono", size: 11 }, color: "#8b8d93", callback: (v) => (v % 3 === 0 ? `${String(v).padStart(2, "0")}h` : "") }, border: { color: "#d6d6d9" } },
          y: { grid: { color: "#efeff0" }, border: { display: false }, ticks: { font: { family: "Geist Mono", size: 11 }, color: "#8b8d93", callback: (v) => `${v > 0 ? "+" : ""}${v}${unit === "%" ? "%" : ""}` } },
        },
      },
      plugins: [bandPlugin],
    });
  }

  let evidenceChart = null;
  function drawEvidence(doc, station) {
    const canvas = $("#evidence-chart");
    if (evidenceChart) { evidenceChart.destroy(); evidenceChart = null; }
    if (!canvas || !doc?.recent_48h) return;
    const r = doc.recent_48h;
    const labels = r.hours.map((k) => k.slice(11, 13) + ":00");
    // neighbour band: per-hour min and max across neighbours
    const nbVals = Object.values(r.neighbours_pm25);
    const bandMin = r.hours.map((_, i) => {
      const vs = nbVals.map((a) => a[i]).filter((v) => v != null);
      return vs.length ? Math.min(...vs) : null;
    });
    const bandMax = r.hours.map((_, i) => {
      const vs = nbVals.map((a) => a[i]).filter((v) => v != null);
      return vs.length ? Math.max(...vs) : null;
    });
    const css = getComputedStyle(document.documentElement);
    const stationColor = css.getPropertyValue("--series-7d").trim() || "#1f9d5c";
    const bandColor = "rgba(160,160,165,0.25)";
    evidenceChart = new Chart(canvas, {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: "Neighbour band (max)", data: bandMax, borderWidth: 0, pointRadius: 0, fill: "+1", backgroundColor: bandColor, spanGaps: true },
          { label: "Neighbour band (min)", data: bandMin, borderWidth: 0, pointRadius: 0, fill: false, spanGaps: true },
          { label: `${station.name.split(",")[0]} PM2.5`, data: r.pm25, borderColor: stationColor, borderWidth: 2, pointRadius: 0, pointHoverRadius: 5, cubicInterpolationMode: "monotone", spanGaps: true, fill: false },
        ],
      },
      options: {
        animation: false,
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { mode: "index", intersect: false,
          callbacks: { label: (ctx) => ctx.dataset.fill !== false ? null : `${ctx.dataset.label}: ${ctx.parsed.y == null ? "–" : ctx.parsed.y.toFixed(1)} µg/m³` } } },
        scales: {
          x: { grid: { display: false }, ticks: { maxTicksLimit: 12, font: { size: 11 } } },
          y: { grid: { color: "rgba(0,0,0,.06)" }, title: { display: true, text: "PM2.5 µg/m³", font: { size: 11 } }, ticks: { font: { size: 11 } } },
        },
      },
    });
  }

  function toggleTable(doc) {
    const box = $("#tablebox");
    if (box.innerHTML) { box.innerHTML = ""; $("#as-table").textContent = tx("Show as table"); return; }
    const a = series(doc, "hour_profile_7d"), b = series(doc, "hour_profile");
    const u = PARAMS[param].unit === "%" ? "%" : " pts";
    box.innerHTML = `<table class="data"><thead><tr><th>${tx("Hour (IST)")}</th><th>${tx("Last 7 days")}</th><th>${tx("Last 28 days")}</th></tr></thead><tbody>${a.map((v, h) => `<tr><td>${String(h).padStart(2, "0")}:00</td><td>${v == null ? "–" : v.toFixed(0) + u}</td><td>${b[h] == null ? "–" : b[h].toFixed(0) + u}</td></tr>`).join("")}</tbody></table>`;
    $("#as-table").textContent = tx("Hide table");
  }

  function spotCheck(k) {
    document.querySelectorAll(".check").forEach((el) => el.classList.toggle("spot", el.dataset.check === k));
  }

  // ---------- every monitor, by area ----------
  const CENTRE = [28.62, 77.215]; // around Connaught Place
  function area(s) {
    for (const [w, a] of [["Noida", "Noida"], ["Ghaziabad", "Ghaziabad"], ["Gurugram", "Gurugram and Manesar"], ["Manesar", "Gurugram and Manesar"], ["Faridabad", "Faridabad"], ["Bahadurgarh", "Bahadurgarh"]]) if (s.name.includes(w)) return a;
    const dy = s.lat - CENTRE[0], dx = (s.lon - CENTRE[1]) * Math.cos(CENTRE[0] * Math.PI / 180);
    if (Math.hypot(dx, dy) * 111 < 5) return "Central Delhi";
    return Math.abs(dy) > Math.abs(dx) ? (dy > 0 ? "North Delhi" : "South Delhi") : (dx > 0 ? "East Delhi" : "West Delhi");
  }
  const AREAS = ["Central Delhi", "North Delhi", "South Delhi", "East Delhi", "West Delhi", "Noida", "Ghaziabad", "Gurugram and Manesar", "Faridabad", "Bahadurgarh"];
  let rosterFilter = "all";

  // the labels only: safe to call again (the language toggle does), unlike renderRoster's listeners
  function drawFilters() {
    const count = (st) => latest.stations.filter((s) => s.status === st).length;
    $("#filters").innerHTML = [["all", tx("All"), latest.stations.length], ...["flag", "watch", "ok", "nodata"].map((st) => [st, STATUS[st].short, count(st)])]
      .map(([f, label, n]) => `<button type="button" data-f="${f}" aria-pressed="${f === rosterFilter}">${f === "all" ? "" : icon(f, 12)}${label} <span class="count">${n}</span></button>`).join("");
  }

  function renderRoster() {
    latest.stations.forEach((s) => { s._area = area(s); });
    drawFilters();
    $("#filters").addEventListener("click", (e) => {
      const b = e.target.closest("[data-f]");
      if (!b) return;
      rosterFilter = b.dataset.f;
      $("#filters").querySelectorAll("[data-f]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      drawRoster();
    });
    $("#roster-q").addEventListener("input", drawRoster);
    $("#areas").addEventListener("click", (e) => {
      const b = e.target.closest("[data-open]");
      if (!b) return;
      select(Number(b.dataset.open), { fly: true });
      mapWindow().scrollIntoView({ behavior: "smooth", block: "center" });
    });
    drawRoster();
  }

  function drawRoster() {
    const q = $("#roster-q").value.trim().toLowerCase();
    const shown = latest.stations.filter((s) => (rosterFilter === "all" || s.status === rosterFilter) && (!q || s.name.toLowerCase().includes(q) || s._area.toLowerCase().includes(q) || tx(s._area).includes(q)));
    const html = AREAS.map((a) => {
      const list = shown.filter((s) => s._area === a).sort((x, y) => ORDER.indexOf(x.status) - ORDER.indexOf(y.status) || x.name.localeCompare(y.name));
      return list.length ? `<section class="area"><h4>${tx(a)} <span class="count">${list.length}</span></h4><div class="chips">${list.map((s) => `<button type="button" data-open="${s.id}" aria-label="${esc(s.name)}: ${STATUS[s.status].label}">${icon(s.status, 12)}${esc(listName(s, latest.stations))}</button>`).join("")}</div></section>` : "";
    }).join("");
    $("#areas").innerHTML = html || `<p class="footnote">${tx("No monitor matches. Try another name or area, or show all.")}</p>`;
  }

  // ---------- search ----------
  function setupSearch() {
    const input = $("#search"), list = $("#search-list"), box = input.closest(".search");
    let items = [], idx = -1;
    const close = () => { list.hidden = true; box.setAttribute("aria-expanded", "false"); idx = -1; };
    const show = () => {
      const q = input.value.trim().toLowerCase();
      items = latest.stations.filter((s) => !q || s.name.toLowerCase().includes(q)).sort((a, b) => a.name.localeCompare(b.name)).slice(0, 8);
      list.innerHTML = items.map((s, i) => `<li role="option" id="opt-${i}" data-id="${s.id}" aria-selected="${i === idx}">${esc(s.name)} ${pill(s.status)}</li>`).join("") || `<li aria-disabled="true">${tx("No station matches")}</li>`;
      list.hidden = false; box.setAttribute("aria-expanded", "true");
    };
    const pick = (id) => { close(); input.value = ""; $("#roster-q").value = ""; drawRoster(); select(id, { fly: true }); $("#live").scrollIntoView({ behavior: "smooth", block: "start" }); };
    input.addEventListener("input", () => { idx = -1; show(); $("#roster-q").value = input.value; drawRoster(); });
    input.addEventListener("focus", show);
    input.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") { idx = Math.min(idx + 1, items.length - 1); show(); e.preventDefault(); }
      else if (e.key === "ArrowUp") { idx = Math.max(idx - 1, 0); show(); e.preventDefault(); }
      else if (e.key === "Enter" && items.length) { pick(items[Math.max(idx, 0)].id); }
      else if (e.key === "Escape") close();
    });
    list.addEventListener("mousedown", (e) => { const li = e.target.closest("li[data-id]"); if (li) pick(Number(li.dataset.id)); });
    input.addEventListener("blur", () => setTimeout(close, 120));
  }

  // the scene may be built after the weather arrived: hand it the wind then
  window.addEventListener("gt3d:ready", () => {
    if (weather && weather.wind_from_deg != null) view?.setWind?.(weather.wind_from_deg, weather.wind_kmh);
    if (firesDoc && firesDoc.count) view?.setFires?.(firesDoc);
  });

  // ---------- ?demo=1: the story, playing by itself ----------
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  function caption(k, text) {
    let el = $("#tour");
    if (!el) { el = document.createElement("div"); el.id = "tour"; el.className = "tour"; el.setAttribute("role", "status"); document.body.appendChild(el); }
    el.innerHTML = `<span class="label">${esc(k)}</span>${text}`;
  }

  // ?capture=1 (video/capture_demo.py): the tour's moves, one at a time, timed to the narration from outside
  if (new URLSearchParams(location.search).has("capture")) {
    window.__gt = { select, enterImmersive, exitImmersive, caption, mark, scrollTo: (sel) => $(sel)?.scrollIntoView({ behavior: "smooth", block: "start" }) };
  }

  async function tour() {
    const pick = (pred, fallback) => (latest.stations.find(pred) || byId.get(fallback) || latest.stations[0]).id;
    const physics = pick((s) => s.checks.physics.status === "flag", 301);
    const history = pick((s) => s.id === 8235 && s.checks.history.status !== "nodata", 8235);
    const n = latest.stations.length;
    mark("tour:start");
    caption("Ground Truth", tr`${n} air-quality monitors across Delhi and NCR, checked every hour.`);
    await wait(3500);
    $("#live").scrollIntoView({ behavior: "smooth", block: "start" });
    await wait(1500);
    enterImmersive();
    caption("Ground Truth", tx("Delhi in 3D. Each mast is a monitor; its column is as tall as its PM2.5 reading, and the smog is thicker where the air is worse."));
    await wait(5000);

    mark("tour:physics");
    await select(physics, { fly: true, spot: "physics" });
    caption(tx("Physics"), tr`${esc(byId.get(physics).name.split(",")[0])} reports readings that can't be real. Its numbers don't add up.`);
    await wait(6500);

    mark("tour:chart");
    await select(235, { fly: true, spot: "neighbours" });
    caption(tx("Neighbours"), tx("Anand Vihar, hour by hour, against the four stations around it. The shaded band is 11:00 to 17:00."));
    await wait(7000);

    mark("tour:history");
    await select(history, { fly: true, spot: "history" });
    caption(tx("History"), tx("Jahangirpuri against its own last three weeks. Worth a look, not proof."));
    await wait(6500);

    mark("tour:advice");
    caption(tx("What to do"), tx("When a station is in doubt, use what the stations around it read right now."));
    document.querySelector("#panel .now")?.scrollIntoView({ behavior: "smooth", block: "center" });
    await wait(5000);
    caption("Ground Truth", tx("A flag means the numbers don't add up. Not that anyone cheated."));
    mark("tour:end");
  }

  function applyLang() {
    document.documentElement.lang = lang;
    const btn = $("#lang-toggle");
    if (btn) { btn.textContent = t().langToggleText; btn.setAttribute("aria-label", t().langToggleLabel); }
    const search = $("#search");
    if (search) { search.setAttribute("placeholder", t().findPlaceholder); search.labels?.[0]?.setAttribute && search.labels[0].textContent === "Find your station" && (search.labels[0].textContent = t().findStation); }
    const rosterQ = $("#roster-q");
    if (rosterQ) rosterQ.setAttribute("placeholder", t().filterPlaceholder);
    // Noto Sans Devanagari for Hindi text
    document.body.classList.toggle("lang-hi", lang === "hi");
  }

  function setupLangToggle() {
    window.GT_I18N.page();
    applyLang();
    $("#lang-toggle")?.addEventListener("click", () => {
      try { localStorage.setItem("gt-lang", lang === "en" ? "hi" : "en"); } catch (_) { return; }
      location.reload();
    });
  }

  document.addEventListener("DOMContentLoaded", () => { setupLangToggle(); boot(); });

  // Fill the suggested citation date
  document.addEventListener("DOMContentLoaded", () => {
    const el = document.getElementById("cite-date");
    if (el) el.textContent = new Date().toISOString().slice(0, 10);
  });
})();
