/* React Bits-inspired Aurora Canvas, SpotlightCards, CountUp & Interactive What-If Simulator */

const state = {
  plan: null,
  activeFilter: "all",
  enabledActions: new Set(),
};

const CAT_LABELS = {
  daily_routine: "Daily Routine",
  indoor_hack: "Indoor Air Hack",
  sustainable_alt: "Sustainable Alternative",
};

// 1. Aurora ambient canvas
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
    t += 0.006;
    ctx.clearRect(0, 0, w, h);

    const blobs = [
      { x: w * (0.25 + 0.12 * Math.sin(t)), y: h * 0.22, r: Math.max(w, h) * 0.42, c: "rgba(56, 189, 248, 0.16)" },
      { x: w * (0.72 + 0.10 * Math.cos(t * 0.8)), y: h * 0.30, r: Math.max(w, h) * 0.38, c: "rgba(52, 211, 153, 0.12)" },
      { x: w * (0.50 + 0.14 * Math.sin(t * 0.6 + 2)), y: h * 0.78, r: Math.max(w, h) * 0.45, c: "rgba(99, 102, 241, 0.11)" },
    ];
    for (const b of blobs) {
      const grad = ctx.createRadialGradient(b.x, b.y, 0, b.x, b.y, b.r);
      grad.addColorStop(0, b.c);
      grad.addColorStop(1, "transparent");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();

// 2. SpotlightCard cursor tracking
document.addEventListener("pointermove", (e) => {
  const card = e.target.closest(".spotlight-card");
  if (!card) return;
  const rect = card.getBoundingClientRect();
  card.style.setProperty("--mx", `${e.clientX - rect.left}px`);
  card.style.setProperty("--my", `${e.clientY - rect.top}px`);
});

// 3. Smooth CountUp helper
function animateCount(el, target, suffix = "") {
  const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (prefersReduced) {
    el.textContent = `${target}${suffix}`;
    return;
  }
  const startVal = parseInt(el.textContent, 10) || 0;
  const duration = 450;
  const startTime = performance.now();

  function tick(now) {
    const p = Math.min(1, (now - startTime) / duration);
    const eased = 1 - Math.pow(1 - p, 3);
    const val = Math.round(startVal + (target - startVal) * eased);
    el.textContent = `${val}${suffix}`;
    if (p < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

// 4. Profile serialization
function readProfile() {
  const manualRaw = document.getElementById("manual_aqi").value.trim();
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
    manual_aqi_override: manualRaw ? Number(manualRaw) : null,
  };
}

// 5. Recompute live What-If impact from toggled actions
function updateImpactMetrics() {
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
  const trees = ((weeklyCo2 * 52) / 21.77).toFixed(1);

  animateCount(document.getElementById("risk-before"), base);
  animateCount(document.getElementById("risk-after"), projectedRisk);
  animateCount(document.getElementById("pm-drop"), dropPct, "%");
  document.getElementById("co2-meta").textContent = `${weeklyCo2.toFixed(1)} kg CO₂e/week · ${trees} trees/yr`;
}

// 6. Render action cards safely using DOM APIs (XSS-safe)
function renderActions() {
  const grid = document.getElementById("actions-grid");
  grid.innerHTML = "";
  if (!state.plan) return;

  state.plan.actions.forEach((act, idx) => {
    if (state.activeFilter !== "all" && act.category !== state.activeFilter) return;

    const card = document.createElement("article");
    const isEnabled = state.enabledActions.has(idx);
    card.className = `spotlight-card action-card${isEnabled ? "" : " inactive"}`;

    const top = document.createElement("div");
    top.className = "action-top";

    const cat = document.createElement("span");
    cat.className = "cat-tag";
    cat.textContent = CAT_LABELS[act.category] || act.category;

    const toggleLabel = document.createElement("label");
    toggleLabel.className = "toggle-switch";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = isEnabled;
    checkbox.setAttribute("aria-label", `Adopt ${act.title}`);
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) state.enabledActions.add(idx);
      else state.enabledActions.delete(idx);
      card.classList.toggle("inactive", !checkbox.checked);
      updateImpactMetrics();
    });
    const toggleTxt = document.createElement("span");
    toggleTxt.textContent = isEnabled ? "Adopted" : "Skipped";
    checkbox.addEventListener("change", () => {
      toggleTxt.textContent = checkbox.checked ? "Adopted" : "Skipped";
    });
    toggleLabel.append(checkbox, toggleTxt);
    top.append(cat, toggleLabel);

    const title = document.createElement("h3");
    title.className = "action-title";
    title.textContent = act.title;

    const steps = document.createElement("p");
    steps.className = "action-steps";
    steps.textContent = act.steps;

    const impactBox = document.createElement("div");
    impactBox.className = "impact-box";
    const impactText = document.createElement("div");
    impactText.textContent = act.direct_impact;

    const chips = document.createElement("div");
    chips.className = "impact-chips";
    const pmChip = document.createElement("span");
    pmChip.textContent = `-${act.pm25_reduction_pct}% PM2.5`;
    const co2Chip = document.createElement("span");
    co2Chip.textContent = `${act.weekly_co2_saved_kg.toFixed(1)} kg CO₂e/wk`;
    const costChip = document.createElement("span");
    costChip.textContent = act.cost_level;
    chips.append(pmChip, co2Chip, costChip);

    impactBox.append(impactText, chips);
    card.append(top, title, steps, impactBox);
    grid.appendChild(card);
  });
}

function renderPlan(data) {
  state.plan = data;
  state.enabledActions = new Set(data.actions.map((_, idx) => idx));

  const aq = data.air_quality;
  animateCount(document.getElementById("aqi-value"), aq.aqi_us);

  const badge = document.getElementById("aqi-tier");
  badge.textContent = aq.severity_tier;
  badge.className = "severity-badge";
  if (aq.aqi_us <= 100) badge.classList.add("ok");
  else if (aq.aqi_us <= 150) badge.classList.add("warn");

  document.getElementById("aqi-meta").textContent = `PM2.5 ${aq.pm25_ug_m3} µg/m³ · ${aq.city} (${aq.source})`;
  document.getElementById("risk-meta").textContent = data.risk_explanation;
  document.getElementById("ai-provider").textContent = data.ai_provider;
  document.getElementById("ai-narrative").textContent = data.ai_narrative;
  document.getElementById("vent-window").textContent = aq.best_ventilation_window;

  updateImpactMetrics();
  renderActions();
}

async function fetchPlan() {
  const errEl = document.getElementById("form-error");
  const btn = document.getElementById("generate-btn");
  errEl.textContent = "";
  btn.disabled = true;

  try {
    const res = await fetch("/api/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(readProfile()),
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail?.[0]?.msg || "Please check your city and inputs.");
    }
    const data = await res.json();
    renderPlan(data);
  } catch (err) {
    errEl.textContent = err.message;
  } finally {
    btn.disabled = false;
  }
}

// Event bindings
document.getElementById("profile-form").addEventListener("submit", (e) => {
  e.preventDefault();
  fetchPlan();
});

document.querySelectorAll(".chip-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.getElementById("city").value = btn.dataset.city;
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
    if (!res.ok) throw new Error(data.detail?.[0]?.msg || "Unable to answer right now.");
    metaEl.textContent = data.ai_provider;
    ansEl.textContent = data.answer;
    wrap.classList.remove("hidden");
  } catch (err) {
    metaEl.textContent = "Validation";
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

// Initial load
fetchPlan();
