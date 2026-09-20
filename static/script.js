document.addEventListener("DOMContentLoaded", () => {
  const canvas = document.getElementById("fx-canvas");
  const ctx = canvas.getContext("2d");
  let particles = [], W, H;
  function resizeCanvas() { W = canvas.width = window.innerWidth; H = canvas.height = window.innerHeight; }
  window.addEventListener("resize", resizeCanvas); resizeCanvas();
  function initParticles() {
    const count = Math.min(70, Math.floor((W * H) / 22000));
    particles = Array.from({ length: count }, () => ({
      x: Math.random() * W, y: Math.random() * H, r: Math.random() * 1.5 + 0.4,
      vy: -(Math.random() * 0.2 + 0.05), vx: (Math.random() - 0.5) * 0.12,
      hue: Math.random() > 0.5 ? "34,211,176" : "245,166,35", alpha: Math.random() * 0.5 + 0.15,
    }));
  }
  initParticles(); window.addEventListener("resize", initParticles);
  function tick() {
    ctx.clearRect(0, 0, W, H);
    for (const p of particles) {
      p.x += p.vx; p.y += p.vy;
      if (p.y < -10) { p.y = H + 10; p.x = Math.random() * W; }
      if (p.x < -10) p.x = W + 10; if (p.x > W + 10) p.x = -10;
      ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${p.hue},${p.alpha})`; ctx.shadowColor = `rgba(${p.hue},0.9)`; ctx.shadowBlur = 6; ctx.fill();
    }
    requestAnimationFrame(tick);
  }
  tick();

  // Design-thinking step navigation
  const steps = ["empathize", "define", "ideate", "prototype", "test"];
  function goto(step) {
    document.querySelectorAll(".dt-panel").forEach(p => p.hidden = p.dataset.panel !== step);
    document.querySelectorAll(".dt-step").forEach(s => s.classList.toggle("active", s.dataset.step === step));
  }
  document.querySelectorAll(".dt-next").forEach(btn => btn.addEventListener("click", () => goto(btn.dataset.goto)));
  document.querySelectorAll(".dt-step").forEach(s => s.addEventListener("click", () => {
    if (s.dataset.step === "test" && document.getElementById("result-readout").textContent === "--") return;
    goto(s.dataset.step);
  }));

  const syncPairs = ["monthly_income_inr", "monthly_rent_inr", "savings_buffer_months", "tenure_months",
                     "dependents", "late_rent_payments_12mo"];
  syncPairs.forEach((id) => {
    const range = document.getElementById(id + "-r"); const num = document.getElementById(id);
    if (!range || !num) return;
    range.addEventListener("input", () => { num.value = range.value; });
    num.addEventListener("input", () => { if (num.value !== "") range.value = num.value; });
  });

  function wireSegmented(containerId) {
    const container = document.getElementById(containerId); if (!container) return;
    const targetSelect = document.getElementById(container.dataset.target);
    container.querySelectorAll(".seg-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        container.querySelectorAll(".seg-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active"); targetSelect.value = btn.dataset.value;
      });
    });
  }
  ["eviction-seg", "health-seg", "migrant-seg"].forEach(wireSegmented);

  const form = document.getElementById("predict-form");
  const submitBtn = document.getElementById("submit-btn");
  const errorNote = document.getElementById("form-error");
  const readout = document.getElementById("result-readout");
  const hint = document.getElementById("result-hint");
  const derivedBox = document.getElementById("result-derived");
  const derivedRentPct = document.getElementById("derived-rent-pct");
  const derivedTopFactors = document.getElementById("derived-top-factors");
  const ringFill = document.getElementById("ring-fill");
  const liquidFill = document.getElementById("liquid-fill");
  const categoryBadge = document.getElementById("category-badge");
  const houseWrap = document.getElementById("pulse-ring");

  const RING_CIRCUMFERENCE = 653.45;
  const LIQUID_TOP = 8, LIQUID_BASE = 92;
  let currentDisplayed = 0;

  function animateRing(pct) {
    const fraction = Math.max(0, Math.min(pct / 100, 1));
    ringFill.style.strokeDashoffset = RING_CIRCUMFERENCE * (1 - fraction);
  }
  function animateLiquid(pct) {
    const fraction = Math.max(0, Math.min(pct / 100, 1));
    const fillY = LIQUID_BASE - fraction * (LIQUID_BASE - LIQUID_TOP);
    liquidFill.setAttribute("y", fillY); liquidFill.setAttribute("height", LIQUID_BASE - fillY);
  }
  function animateCountUp(from, to, ms) {
    const start = performance.now();
    function step(now) {
      const t = Math.min((now - start) / ms, 1); const eased = 1 - Math.pow(1 - t, 3);
      const value = from + (to - from) * eased;
      readout.textContent = value.toFixed(1) + "%";
      if (t < 1) requestAnimationFrame(step); else { readout.textContent = to.toFixed(1) + "%"; currentDisplayed = to; }
    }
    requestAnimationFrame(step);
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorNote.textContent = "";
    submitBtn.disabled = true;
    submitBtn.querySelector(".btn-label").textContent = "ASSESSING\u2026";

    const payload = {
      monthly_income_inr: document.getElementById("monthly_income_inr").value,
      monthly_rent_inr: document.getElementById("monthly_rent_inr").value,
      city: document.getElementById("city").value,
      employment_type: document.getElementById("employment_type").value,
      savings_buffer_months: document.getElementById("savings_buffer_months").value,
      tenure_months: document.getElementById("tenure_months").value,
      dependents: document.getElementById("dependents").value,
      late_rent_payments_12mo: document.getElementById("late_rent_payments_12mo").value,
      eviction_notice_5yr: document.getElementById("eviction_notice_5yr").value,
      health_shock_12mo: document.getElementById("health_shock_12mo").value,
      migrant_worker: document.getElementById("migrant_worker").value,
      social_support: document.getElementById("social_support").value,
      education: document.getElementById("education").value,
    };

    try {
      const response = await fetch("/predict", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) { errorNote.textContent = data.error || "Something went wrong. Check the values and try again."; return; }

      document.querySelectorAll(".dt-panel").forEach(p => p.hidden = p.dataset.panel !== "test");
      document.querySelectorAll(".dt-step").forEach(s => s.classList.toggle("active", s.dataset.step === "test"));

      const prob = data.probability;
      animateCountUp(currentDisplayed, prob, 800);
      animateRing(prob); animateLiquid(prob);
      houseWrap.classList.remove("pulsing"); void houseWrap.offsetWidth; houseWrap.classList.add("pulsing");

      categoryBadge.textContent = data.label;
      categoryBadge.className = "category-badge " + data.css_class;
      categoryBadge.hidden = false;

      derivedRentPct.textContent = data.rent_to_income_pct + "%";
      derivedTopFactors.textContent = data.top_factors.slice(0, 3).join(", ");
      derivedBox.hidden = false;
      hint.textContent = "Estimate from a documented risk-factor model \u2014 an awareness tool, not an eligibility or clinical decision.";
    } catch (err) {
      errorNote.textContent = "Could not reach the server. Please try again.";
    } finally {
      submitBtn.disabled = false;
      submitBtn.querySelector(".btn-label").textContent = "RUN ASSESSMENT";
    }
  });
});