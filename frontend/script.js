// Point this at wherever your FastAPI backend is running.
const API_BASE = "https://pricemonitor-backend.onrender.com";

let token = safeGet("token");
let allProducts = [];
let activeCategory = "All";
let currentPage = "home";
let priceChart = null;

function safeGet(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }
function safeSet(key, value) { try { localStorage.setItem(key, value); } catch (e) {} }

// ================= THEME =================
const themeToggle = document.getElementById("themeToggle");
function applyTheme(theme) {
  document.body.setAttribute("data-theme", theme);
  themeToggle.querySelector(".knob").textContent = theme === "dark" ? "☾" : "☀";
  safeSet("theme", theme);
}
applyTheme(safeGet("theme") || "dark");
themeToggle.onclick = () => {
  const next = document.body.getAttribute("data-theme") === "dark" ? "light" : "dark";
  applyTheme(next);
  if (currentPage === "dashboard") drawChart();
};

// ================= AUTH =================
let authMode = "login";
const authScreen = document.getElementById("authScreen");
const authStatus = document.getElementById("authStatus");
const navLinks = document.getElementById("navLinks");

function showApp() {
  authScreen.classList.add("hidden");
  navLinks.classList.remove("hidden");
  authStatus.innerHTML = `Logged in <a id="logoutLink">Logout</a>`;
  document.getElementById("logoutLink").onclick = logout;
  goToPage("home");
}

function showAuth() {
  authScreen.classList.remove("hidden");
  navLinks.classList.add("hidden");
  authStatus.innerHTML = "";
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
}

function logout() {
  token = null;
  safeSet("token", "");
  showAuth();
}

document.getElementById("authSwitchLink").onclick = (e) => {
  e.preventDefault();
  authMode = authMode === "login" ? "register" : "login";
  document.getElementById("authTitle").textContent = authMode === "login" ? "Login" : "Register";
  document.getElementById("authSubmitBtn").textContent = authMode === "login" ? "Login" : "Create account";
  document.getElementById("authSwitchText").textContent = authMode === "login" ? "Don't have an account?" : "Already have an account?";
  document.getElementById("authSwitchLink").textContent = authMode === "login" ? "Register" : "Login";
};

document.getElementById("authSubmitBtn").onclick = async () => {
  const email = document.getElementById("authEmail").value.trim();
  const password = document.getElementById("authPassword").value;
  const errorEl = document.getElementById("authError");
  errorEl.textContent = "";
  if (!email || !password) { errorEl.textContent = "Enter both email and password."; return; }

  try {
    if (authMode === "register") {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Registration failed");
      authMode = "login";
      document.getElementById("authTitle").textContent = "Login";
    }
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);
    const loginRes = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form,
    });
    if (!loginRes.ok) throw new Error((await loginRes.json()).detail || "Login failed");
    const data = await loginRes.json();
    token = data.access_token;
    safeSet("token", token);
    showApp();
  } catch (err) {
    errorEl.textContent = err.message;
  }
};

// ================= NAVIGATION =================
document.querySelectorAll(".nav-links button").forEach((btn) => {
  btn.onclick = () => goToPage(btn.dataset.page);
});

function goToPage(pageName) {
  currentPage = pageName;
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
  document.getElementById(`view-${pageName}`).classList.add("active");
  document.querySelectorAll(".nav-links button").forEach(b => b.classList.toggle("active", b.dataset.page === pageName));

  if (pageName === "home") loadProducts();
  if (pageName === "dashboard") loadProducts();
  if (pageName === "products") loadProducts();
  if (pageName === "settings") loadSettings();
}

// ================= ADD PRODUCT =================
document.getElementById("addProductBtn").onclick = async () => {
  const url = document.getElementById("productUrl").value.trim();
  const targetPrice = parseFloat(document.getElementById("targetPrice").value);
  const statusEl = document.getElementById("addProductStatus");
  if (!url || !targetPrice) { statusEl.textContent = "Enter a product URL and target price."; return; }

  statusEl.textContent = "Fetching price, checking the other platform too... this can take a few seconds.";
  try {
    const res = await fetch(`${API_BASE}/products`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify({ url, target_price: targetPrice }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || "Could not add product");
    statusEl.textContent = "Product added and being tracked.";
    document.getElementById("productUrl").value = "";
    document.getElementById("targetPrice").value = "";
    loadProducts();
  } catch (err) {
    statusEl.textContent = err.message;
  }
};

// ================= LOAD PRODUCTS =================
async function loadProducts() {
  const res = await fetch(`${API_BASE}/products`, { headers: { "Authorization": `Bearer ${token}` } });
  if (!res.ok) return;
  allProducts = await res.json();

  if (currentPage === "home") renderHome();
  if (currentPage === "dashboard") renderDashboard();
  if (currentPage === "products") renderProductsPage();
}

// ================= HELPERS =================
function pairProducts(products) {
  const seen = new Set();
  const pairs = [];
  products.forEach((p) => {
    if (seen.has(p.id)) return;
    const twin = products.find((x) => x.id === p.matched_product_id);
    if (twin) { seen.add(p.id); seen.add(twin.id); }
    pairs.push({ main: p, twin });
  });
  return pairs;
}

function productCardHTML(pair) {
  const { main: p, twin } = pair;
  const cheaper = twin && twin.current_price < p.current_price ? twin : p;
  const hitTarget = cheaper.current_price != null && cheaper.current_price <= cheaper.target_price;
  const imageHTML = p.image_url
    ? `<img src="${p.image_url}" alt="${p.name}" onerror="this.parentElement.innerHTML='<span class=&quot;no-image&quot;>No image</span>'">`
    : `<span class="no-image">No image</span>`;

  return `
    <div class="product-card">
      <div class="image-wrap" onclick="showChart(${p.id}, '${p.name.replace(/'/g, "\\'")}')">${imageHTML}</div>
      <div class="card-body">
        ${p.category ? `<span class="category-tag">${p.category}</span>` : ''}
        <div class="name" onclick="showChart(${p.id}, '${p.name.replace(/'/g, "\\'")}')">${p.name}</div>
        <a href="${p.url}" target="_blank" rel="noopener" class="site-row ${cheaper === p || !twin ? 'cheaper' : ''}">
          <span class="site-label">${p.site} ↗</span>
          <span class="price">${p.current_price != null ? '₹' + p.current_price.toLocaleString() : '—'}</span>
        </a>
        ${twin ? `
        <a href="${twin.url}" target="_blank" rel="noopener" class="site-row ${cheaper === twin ? 'cheaper' : ''}">
          <span class="site-label">${twin.site} ↗</span>
          <span class="price">${twin.current_price != null ? '₹' + twin.current_price.toLocaleString() : '—'}</span>
        </a>` : ''}
        <div class="target-row">
          <span>Target: ₹${p.target_price.toLocaleString()}</span>
          ${hitTarget ? '<span class="badge lowest">Target hit!</span>' : ''}
        </div>
      </div>
    </div>
  `;
}

// ================= HOME PAGE =================
function renderHome() {
  const totalProducts = allProducts.length;
  const targetsHit = allProducts.filter(p => p.current_price != null && p.current_price <= p.target_price).length;
  const categories = new Set(allProducts.map(p => p.category).filter(Boolean));

  document.getElementById("heroStats").innerHTML = `
    <div class="hero-stat"><b class="mono">${totalProducts}</b><span>products tracked</span></div>
    <div class="hero-stat"><b class="mono">${targetsHit}</b><span>targets hit</span></div>
    <div class="hero-stat"><b class="mono">${categories.size}</b><span>categories</span></div>
  `;

  const monitorList = document.getElementById("monitorList");
  if (allProducts.length === 0) {
    monitorList.innerHTML = `<p class="sub">No products tracked yet. Go to Dashboard to add one.</p>`;
  } else {
    monitorList.innerHTML = allProducts.slice(0, 5).map(p => `
      <div class="monitor-row">
        <div class="name">${p.name.slice(0, 34)}${p.name.length > 34 ? '…' : ''}<small>${p.site}</small></div>
        <div class="price">₹${p.current_price != null ? p.current_price.toLocaleString() : '—'}</div>
      </div>
    `).join("");
  }
}

// ================= DASHBOARD PAGE =================
function renderDashboard() {
  const pairs = pairProducts(allProducts);
  const totalProducts = allProducts.length;
  const targetsHit = allProducts.filter(p => p.current_price != null && p.current_price <= p.target_price).length;
  const categories = new Set(allProducts.map(p => p.category).filter(Boolean));

  const totalCurrent = allProducts.reduce((sum, p) => sum + (p.current_price || 0), 0);
  const totalTarget = allProducts.reduce((sum, p) => sum + (p.target_price || 0), 0);

  document.getElementById("kpiGrid").innerHTML = `
    <div class="kpi-card"><div class="value">${totalProducts}</div><div class="label">Products tracked</div></div>
    <div class="kpi-card"><div class="value">${targetsHit}</div><div class="label">Targets hit</div></div>
    <div class="kpi-card"><div class="value">₹${totalCurrent.toLocaleString()}</div><div class="label">Total current price</div></div>
    <div class="kpi-card"><div class="value">₹${totalTarget.toLocaleString()}</div><div class="label">Total target price</div></div>
  `;

  document.getElementById("dashboardGrid").innerHTML = pairs.slice(0, 6).map(productCardHTML).join("")
    || `<p class="sub">No products yet — add one above.</p>`;
}

// ================= PRODUCTS PAGE =================
function renderProductsPage() {
  const categories = ["All", ...new Set(allProducts.map(p => p.category || "Other"))];
  document.getElementById("categoryChips").innerHTML = categories.map(cat =>
    `<div class="chip ${cat === activeCategory ? 'active' : ''}" onclick="setCategory('${cat}')">${cat}</div>`
  ).join("");

  const query = (document.getElementById("searchInput").value || "").toLowerCase();
  let filtered = activeCategory === "All" ? allProducts : allProducts.filter(p => (p.category || "Other") === activeCategory);
  filtered = filtered.filter(p => p.name.toLowerCase().includes(query));

  const pairs = pairProducts(filtered);
  document.getElementById("productsGrid").innerHTML = pairs.map(productCardHTML).join("")
    || `<p class="sub">No products match.</p>`;
}
function setCategory(cat) { activeCategory = cat; renderProductsPage(); }
document.getElementById("searchInput").addEventListener("input", renderProductsPage);

// ================= PRICE CHART =================
let lastChartProduct = null;

async function showChart(productId, name) {
  const res = await fetch(`${API_BASE}/products/${productId}`, { headers: { "Authorization": `Bearer ${token}` } });
  if (!res.ok) return;
  const product = await res.json();
  lastChartProduct = { name, product };

  goToPage("dashboard");
  document.getElementById("chartSection").classList.remove("hidden");
  document.getElementById("chartTitle").textContent = `Price history — ${name}`;
  drawChart();
  document.getElementById("chartSection").scrollIntoView({ behavior: "smooth" });
}

function drawChart() {
  if (!lastChartProduct) return;
  const { product } = lastChartProduct;
  const style = getComputedStyle(document.body);
  const accent = style.getPropertyValue("--accent").trim();
  const muted = style.getPropertyValue("--text-muted").trim();
  const grid = style.getPropertyValue("--border").trim();

  const labels = product.price_history.map((h) => new Date(h.checked_at).toLocaleDateString());
  const prices = product.price_history.map((h) => h.price);

  if (priceChart) priceChart.destroy();
  priceChart = new Chart(document.getElementById("priceChart"), {
    type: "line",
    data: { labels, datasets: [{
      label: "Price (₹)", data: prices, borderColor: accent,
      backgroundColor: accent + "22", fill: true, tension: 0.3, pointRadius: 2, borderWidth: 2,
    }]},
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: muted }, grid: { display: false } },
        y: { ticks: { color: muted, callback: v => '₹' + v }, grid: { color: grid } },
      },
    },
  });
}

// ================= SETTINGS =================
async function loadSettings() {
  const res = await fetch(`${API_BASE}/settings`, { headers: { "Authorization": `Bearer ${token}` } });
  if (!res.ok) return;
  const data = await res.json();

  document.getElementById("settingsEmail").textContent = data.email;
  document.getElementById("settingsName").value = data.name || "";
  document.getElementById("settingsPhone").value = data.phone || "";
  document.getElementById("settingsAge").value = data.age || "";
  document.getElementById("profileEmailDisplay").textContent = data.email;
  document.getElementById("profileNameDisplay").textContent = data.name || "Your name";

  const picWrap = document.getElementById("profilePicWrap");
  const initial = (data.name || data.email)[0].toUpperCase();
  if (data.profile_picture_url) {
    picWrap.innerHTML = `<img src="${data.profile_picture_url}" alt="Profile"><div class="pic-edit-overlay">Change</div>`;
  } else {
    picWrap.innerHTML = `<span id="profileInitial">${initial}</span><div class="pic-edit-overlay">Change</div>`;
  }
  picWrap.onclick = () => document.getElementById("picFileInput").click();
}

document.getElementById("saveSettingsBtn").onclick = async () => {
  const name = document.getElementById("settingsName").value.trim();
  const phone = document.getElementById("settingsPhone").value.trim();
  const ageVal = document.getElementById("settingsAge").value;
  const statusEl = document.getElementById("settingsStatus");
  try {
    const res = await fetch(`${API_BASE}/settings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify({ name: name || null, phone: phone || null, age: ageVal ? parseInt(ageVal) : null }),
    });
    if (!res.ok) throw new Error("Could not save settings");
    statusEl.textContent = "Settings saved.";
    loadSettings();
  } catch (err) {
    statusEl.textContent = err.message;
  }
};

// Profile picture: read the chosen file, convert to a data URL, save it as profile_picture_url
document.getElementById("picFileInput").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const statusEl = document.getElementById("settingsStatus");

  const reader = new FileReader();
  reader.onload = async () => {
    const dataUrl = reader.result;
    try {
      const res = await fetch(`${API_BASE}/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
        body: JSON.stringify({ profile_picture_url: dataUrl }),
      });
      if (!res.ok) throw new Error("Could not save photo");
      statusEl.textContent = "Profile photo updated.";
      loadSettings();
    } catch (err) {
      statusEl.textContent = err.message;
    }
  };
  reader.readAsDataURL(file);
});

document.getElementById("logoutBtnSettings").onclick = logout;

// ================= BOOT =================
if (token) {
  showApp();
} else {
  showAuth();
}