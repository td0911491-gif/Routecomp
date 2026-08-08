// --- Typed header line ---
const HEADER_CMD = "./compare-routes --mode=all";
const headerEl = document.getElementById("headerCmd");
let i = 0;
(function typeHeader() {
  if (i <= HEADER_CMD.length) {
    headerEl.textContent = HEADER_CMD.slice(0, i);
    i++;
    setTimeout(typeHeader, 35);
  }
})();

// --- Mode toggle (fields vs free text) ---
const modeBtns = document.querySelectorAll(".mode-btn");
const fieldsForm = document.getElementById("fieldsForm");
const freetextForm = document.getElementById("freetextForm");

modeBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    modeBtns.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const mode = btn.dataset.mode;
    fieldsForm.classList.toggle("hidden", mode !== "fields");
    freetextForm.classList.toggle("hidden", mode !== "freetext");
  });
});

// --- Elements ---
const statusLine = document.getElementById("statusLine");
const errorPanel = document.getElementById("errorPanel");
const resultsPanel = document.getElementById("resultsPanel");
const resultsBody = document.getElementById("resultsBody");
const routeLabel = document.getElementById("routeLabel");
const routeDistances = document.getElementById("routeDistances");
const aiSummary = document.getElementById("aiSummary");

function setStatus(text) {
  statusLine.textContent = text;
  statusLine.classList.toggle("hidden", !text);
}
function setError(text) {
  errorPanel.textContent = text;
  errorPanel.classList.toggle("hidden", !text);
}
function comfortDots(level) {
  let out = "";
  for (let n = 1; n <= 5; n++) {
    out += `<span class="${n <= level ? "on" : "off"}">●</span>`;
  }
  return out;
}

async function runCompare(payload) {
  setError("");
  resultsPanel.classList.add("hidden");
  setStatus("resolving locations, computing routes, asking the model...");

  try {
    const res = await fetch("/api/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok) {
      setStatus("");
      setError(data.error || "Something went wrong.");
      return;
    }

    setStatus("");
    renderResults(data);
  } catch (err) {
    setStatus("");
    setError("Network error reaching the server. Is the Flask app running?");
  }
}

function renderResults(data) {
  routeLabel.textContent = `${data.origin.display_name} → ${data.destination.display_name}`;
  routeDistances.textContent = `road: ${data.road_km} km · air: ${data.air_km} km`;

  resultsBody.innerHTML = "";
  data.options.forEach((o) => {
    const tags = [];
    if (o.mode === data.badges.cheapest) tags.push('<span class="badge">cheapest</span>');
    if (o.mode === data.badges.fastest) tags.push('<span class="badge">fastest</span>');
    if (o.mode === data.badges.most_luxurious) tags.push('<span class="badge">luxury</span>');

    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${o.mode}</td>
      <td>${o.distance_km} km</td>
      <td>${o.duration_hours} h</td>
      <td>$${o.cost_usd} · ₹${Math.round(o.cost_inr).toLocaleString('en-IN')}</td>
      <td class="comfort-dots">${comfortDots(o.comfort)}</td>
      <td>${tags.join("") || "&mdash;"}</td>
    `;
    resultsBody.appendChild(row);
  });

  aiSummary.textContent = data.summary;
  resultsPanel.classList.remove("hidden");
}

document.getElementById("fieldsForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const origin = document.getElementById("originInput").value.trim();
  const destination = document.getElementById("destInput").value.trim();
  if (!origin || !destination) return;
  runCompare({ origin, destination });
});

document.getElementById("freetextForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const query = document.getElementById("freetextInput").value.trim();
  if (!query) return;
  runCompare({ query });
});
