/* Visual-first React Bits-inspired dashboard: Aurora, SpotlightCard, Radial Gauge, 24h Smog Curve & What-If Simulator */

const state = {
  plan: null,
  activeFilter: "all",
  enabledActions: new Set(),
};

const SVG_ICONS = {
  daily_routine: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 15"/></svg>',
  indoor_hack: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 10l9-7 9 7v10a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z"/></svg>',
  sustainable_alt: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/></svg>',
};

// 1. Aurora canvas
(function initAurora() {
  const canvas = document.getElementById("aurora-canvas");
  if (!canvas || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const ctx = canvas.getContext("2d");
  let w = 0, h = 0, t = 0;

  function resize() {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener("resize", resize);

  function frame() {
    t += 0.005;
    ctx.clearRect(0, 0, w, h);
    const blobs = [
      { x: w * (0.22 + 0.1 * Math.sin(t)), y: h * 0.2, r: Math.max(w, h) * 0.42, c: "rgba(56, 189, 248, 0.16)" },
      { x: w * (0.76 + 0.1 * Math.cos(t * 0.8)), y: h * 0.28, r: Math.max(w, h) * 0.36, c: "rgba(52, 211, 153, 0.13)" },
      { x: w * (0.5 + 0.12 * Math.sin(t * 0.6 + 2)), y: h * 0.82, r: Math.max(w, h) * 0.42, c: "rgba(99, 102, 241, 0.11)" },
    ];
    for (const b of blobs) {
      const g = ctx.createRadialGradient(b.x, b.y, 0, b.x, b.y, b.r);
      g.addColorStop(0, b.c);
      g.addColorStop(1, "transparent");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, w, h);
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();

// 2. Spotlight cursor tracking
document.addEventListener("pointermove", (e) => {
  const card = e.target.closest(".spotlight-card");
  if (!card) return;
  const r = card.getBoundingClientRect();
  card.style.setProperty("--mx", `${e.clientX - r.left}px`);
  card.style.setProperty("--my", `${e.clientY - r.top}px`);
});

// 3. Smooth CountUp
function animateCount(el, target, suffix = "", decimals = 0) {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduced) {
    el.textContent = `${Number(target).toFixed(decimals)}${suffix}`;
    return;
  }
  const startVal = parseFloat(el.textContent) || 0;
  const startTime = performance.now();
  function tick(now) {
    const p = Math.min(1, (now - startTime) / 420);
    const eased = 1 - Math.pow(1 - p, 3);
    const val = startVal + (target - startVal) * eased;
    el.textContent = `${val.toFixed(decimals)}${suffix}`;
    if (p < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

// 4. 24-hour winter smog diurnal curve SVG generator
function renderSmogCurve(aqi) {
  const pts = [];
  // Typical winter boundary-layer inversion: high 06:00-09:00 & 19:00-23:00, dip 13:00-15:30
  const profile = [
    1.05, 1.02, 1.0, 1.04, 1.12, 1.22, 1.32, 1.35, 1.24, 1.05, 0.86, 0.72,
    0.62, 0.56, 0.58, 0.65, 0.78, 0.95, 1.15, 1.28, 1.30, 1.22, 1.15, 1.08,
  ];
  const maxVal = Math.max(180, aqi * 1.4);
  for (let i = 0; i < 24; i++) {
    const x = 12 + (i / 23) * 396;
    const val = Math.min(500, aqi * profile[i]);
    const y = 126 - (val / maxVal) * 102;
    pts.push([x, Math.max(14, Math.min(128, y))]);
  }
  const lineD = pts.map(([x, y], i) => `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  const areaD = `${lineD} L 408 132 L 12 132 Z`;
  document.getElementById("smog-line").setAttribute("d", lineD);
  document.getElementById("smog-area").setAttribute("d", areaD);

  const band = document.getElementById("safe-band");
  const ventShort = document.getElementById("vent-short");
  if (aqi > 300) {
    band.setAttribute("fill", "rgba(251,113,133,0.12)");
    band.setAttribute("stroke", "rgba(251,113,133,0.4)");
    ventShort.textContent = "KEEP SEALED";
  } else {
    band.setAttribute("fill", "rgba(52,211,153,0.12)");
    band.setAttribute("stroke", "rgba(52,211,153,0.38)");
    ventShort.textContent = aqi <= 100 ? "ALL DAY SAFE" : "13:00–15:30 SAFE";
  }
}

// 5. Read profile
function readProfile() {
  const sliderVal = Number(document.getElementById("aqi-slider").value);
  return {
    city: document.getElementById("city").value.trim(),
    household_size: Number(document.getElementById("household_size").value) || 1,
    has_children: document.getElementById("has_children").checked,
    has_elderly: document.getElementById("has_elderly").checked,
    has_respiratory_condition: document.getElementById("has_respiratory").checked,
    commute_mode: document.getElementById("commute_mode").value,
    commute_km_per_day: Number(document.getElementById("commute_km").value) || 0,
    home_type: document.getElementById("home_type").value,
    cooking_fuel: document.getElementById("cooking_fuel").value,
    budget_tier: document.getElementById("budget_tier").value,
    manual_aqi_override: sliderVal > 0 ? sliderVal : null,
  };
}

// 6. Live What-If recalculation
function updateImpactVisuals() {
  if (!state.plan) return;
  const base = state.plan.impact.baseline_risk_score;
  let remaining = 1.0;
  let weeklyCo2 = 0.0;

  state.plan.actions.forEach((act, idx) => {
    if (state.enabledActions.has(idx)) {
      remaining *= 1 - act.pm25_reduction_pct / 100;
      weeklyCo2 += act.weekly_co2_saved_kg;
    }
  });

  const dropPct = state.enabledActions.size === 0 ? 0 : Math.min(85, Math.round((1 - remaining) * 100));
  const projectedRisk = Math.max(5, Math.round(base * (1 - dropPct / 120)));
  const trees = (weeklyCo2 * 52) / 21.77;

  document.getElementById("pm-drop-badge").textContent = `-${dropPct}% PM2.5`;
  animateCount(document.getElementById("risk-before"), base, "/100");
  animateCount(document.getElementById("risk-after"), projectedRisk, "/100");
  document.getElementById("risk-before-bar").style.width = `${base}%`;
  document.getElementById("risk-after-bar").style.width = `${projectedRisk}%`;
  animateCount(document.getElementById("co2-week"), weeklyCo2, "", 1);
  animateCount(document.getElementById("trees-yr"), trees, "", 1);
}

function createActionCard(act, idx) {
  const card = document.createElement("article");
  const isEnabled = state.enabledActions.has(idx);
  card.className = `spotlight-card action-card${isEnabled ? "" : " inactive"}`;

  const top = document.createElement("div");
  top.className = "action-top";

  const iconWrap = document.createElement("span");
  const catClassMap = { indoor_hack: " indoor", sustainable_alt: " sustain" };
  iconWrap.className = `act-icon-wrap${catClassMap[act.category] || ""}`;
  iconWrap.innerHTML = SVG_ICONS[act.category] || SVG_ICONS.daily_routine;

  const toggleLabel = document.createElement("label");
  toggleLabel.className = "toggle-switch";
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = isEnabled;
  checkbox.setAttribute("aria-label", `Adopt ${act.title}`);
  const toggleTxt = document.createElement("span");
  toggleTxt.textContent = isEnabled ? "On" : "Off";
  checkbox.addEventListener("change", () => {
    if (checkbox.checked) state.enabledActions.add(idx);
    else state.enabledActions.delete(idx);
    card.classList.toggle("inactive", !checkbox.checked);
    toggleTxt.textContent = checkbox.checked ? "On" : "Off";
    updateImpactVisuals();
  });
  toggleLabel.append(checkbox, toggleTxt);
  top.append(iconWrap, toggleLabel);

  const title = document.createElement("h3");
  title.className = "action-title";
  title.textContent = act.title;

  const steps = document.createElement("p");
  steps.className = "action-steps";
  steps.textContent = act.steps.split(";")[0].replace(/\.+$/, "") + ".";

  const meter = document.createElement("div");
  meter.className = "act-meter";

  const mHead = document.createElement("div");
  mHead.className = "act-meter-head";
  const lbl = document.createElement("span");
  lbl.textContent = "PM2.5 Cut";
  const pct = document.createElement("span");
  pct.textContent = `-${act.pm25_reduction_pct}%`;
  mHead.append(lbl, pct);

  const track = document.createElement("div");
  track.className = "act-track";
  const fill = document.createElement("div");
  fill.className = "act-fill";
  fill.style.width = `${Math.min(100, act.pm25_reduction_pct * 1.5)}%`;
  track.appendChild(fill);

  const chips = document.createElement("div");
  chips.className = "act-chips";
  const c1 = document.createElement("span");
  c1.textContent = `${act.weekly_co2_saved_kg.toFixed(1)} kg CO₂/wk`;
  const c2 = document.createElement("span");
  c2.textContent = act.cost_level;
  chips.append(c1, c2);

  meter.append(mHead, track, chips);
  card.append(top, title, steps, meter);
  return card;
}

// 7. Render visual action cards (concise, scannable)
function renderActions() {
  const grid = document.getElementById("actions-grid");
  grid.innerHTML = "";
  if (!state.plan) return;

  state.plan.actions.forEach((act, idx) => {
    if (state.activeFilter === "all" || act.category === state.activeFilter) {
      grid.appendChild(createActionCard(act, idx));
    }
  });
}

function renderPlan(data) {
  state.plan = data;
  state.enabledActions = new Set(data.actions.map((_, i) => i));

  const aq = data.air_quality;
  document.getElementById("city-title").textContent = aq.city.toUpperCase();
  document.getElementById("aqi-source").textContent = aq.source.includes("Live") ? "LIVE API" : aq.source.includes("Sim") ? "SIMULATED" : "BASELINE";

  // Radial gauge arc (251.2 full arc for 0..450 AQI)
  animateCount(document.getElementById("aqi-value"), aq.aqi_us);
  const ratio = Math.min(1, aq.aqi_us / 450);
  document.getElementById("aqi-arc").style.strokeDashoffset = (251.2 * (1 - ratio)).toFixed(1);

  const tierEl = document.getElementById("aqi-tier");
  tierEl.textContent = aq.severity_tier;
  tierEl.className = "gauge-tier";
  if (aq.aqi_us <= 100) tierEl.classList.add("ok");
  else if (aq.aqi_us <= 150) tierEl.classList.add("warn");

  // Pollutant bars
  document.getElementById("pm25-val").textContent = `${aq.pm25_ug_m3}`;
  document.getElementById("pm10-val").textContent = `${aq.pm10_ug_m3}`;
  document.getElementById("no2-val").textContent = `${aq.no2_ug_m3}`;
  document.getElementById("pm25-fill").style.width = `${Math.min(100, (aq.pm25_ug_m3 / 250) * 100)}%`;
  document.getElementById("pm10-fill").style.width = `${Math.min(100, (aq.pm10_ug_m3 / 350) * 100)}%`;
  document.getElementById("no2-fill").style.width = `${Math.min(100, (aq.no2_ug_m3 / 120) * 100)}%`;

  renderSmogCurve(aq.aqi_us);
  document.getElementById("vent-window").textContent = `Window: ${aq.best_ventilation_window}`;
  document.getElementById("ai-provider").textContent = data.ai_provider;
  document.getElementById("ai-narrative").textContent = data.ai_narrative;

  updateImpactVisuals();
  renderActions();
}

async function fetchPlan() {
  const errEl = document.getElementById("form-error");
  errEl.textContent = "";
  try {
    const res = await fetch("/api/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(readProfile()),
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail?.[0]?.msg || "Check city name.");
    }
    renderPlan(await res.json());
  } catch (err) {
    errEl.textContent = err.message;
  }
}

// Event listeners
document.getElementById("profile-form").addEventListener("submit", (e) => {
  e.preventDefault();
  fetchPlan();
});

document.querySelectorAll(".chip-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".chip-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("city").value = btn.dataset.city;
    fetchPlan();
  });
});

const slider = document.getElementById("aqi-slider");
slider.addEventListener("input", () => {
  const v = Number(slider.value);
  document.getElementById("slider-val").textContent = v > 0 ? `${v} AQI` : "Live Auto";
});
slider.addEventListener("change", fetchPlan);

document.querySelectorAll(".mode-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".mode-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("commute_mode").value = btn.dataset.commute;
    fetchPlan();
  });
});

document.querySelectorAll(".seg-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".seg-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("budget_tier").value = btn.dataset.budget;
    fetchPlan();
  });
});

["has_children", "has_elderly", "has_respiratory", "home_type", "cooking_fuel", "household_size", "commute_km"].forEach((id) => {
  document.getElementById(id).addEventListener("change", fetchPlan);
});

document.querySelectorAll(".tab-btn").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((t) => {
      t.classList.remove("active");
      t.setAttribute("aria-selected", "false");
    });
    tab.classList.add("active");
    tab.setAttribute("aria-selected", "true");
    state.activeFilter = tab.dataset.filter;
    renderActions();
  });
});

document.getElementById("contrast-toggle").addEventListener("click", (e) => {
  const active = document.body.classList.toggle("high-contrast");
  e.currentTarget.setAttribute("aria-pressed", String(active));
});

async function submitChat(question) {
  const wrap = document.getElementById("chat-answer-wrap");
  const ansEl = document.getElementById("chat-answer");
  const metaEl = document.getElementById("chat-provider");
  const btn = document.getElementById("chat-btn");
  btn.disabled = true;
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile: readProfile(), question }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail?.[0]?.msg || "Unable to answer.");
    metaEl.textContent = data.ai_provider;
    ansEl.textContent = data.answer;
    wrap.classList.remove("hidden");
  } catch (err) {
    metaEl.textContent = "Error";
    ansEl.textContent = err.message;
    wrap.classList.remove("hidden");
  } finally {
    btn.disabled = false;
  }
}

document.getElementById("chat-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const q = document.getElementById("chat-input").value.trim();
  if (q.length >= 3) submitChat(q);
});

document.querySelectorAll(".prompt-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    document.getElementById("chat-input").value = chip.dataset.q;
    submitChat(chip.dataset.q);
  });
});

fetchPlan();
