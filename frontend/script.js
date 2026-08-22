// Point this at wherever your FastAPI backend is running.
// IMPORTANT: update this to your NEW backend's URL once you deploy it.
const API_BASE = "https://pricelens-backend.onrender.com";

let token = safeGet("token");
let allProducts = [];
let activeCategory = "All";
let currentPage = "home";
let priceChart = null;
let categoryPieChart = null;
let siteBarChart = null;
let pendingVerifyEmail = "";
let pendingResetEmail = "";

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
  if (currentPage === "dashboard") { drawChart(); drawCategoryPie(); if (siteBarChart) drawSiteBar(lastGroup); }
};

// ================= EYE ICON TOGGLE =================
document.querySelectorAll(".eye-icon").forEach((icon) => {
  icon.onclick = () => {
    const input = document.getElementById(icon.dataset.target);
    if (input.type === "password") { input.type = "text"; icon.textContent = "🙈"; }
    else { input.type = "password"; icon.textContent = "👁"; }
  };
});

// ================= SCREEN SWITCHING =================
const screens = ["welcomeScreen", "loginScreen", "registerScreen", "verifyScreen", "forgotScreen", "resetScreen"];
function showScreen(id) {
  screens.forEach(s => document.getElementById(s).classList.add("hidden"));
  document.getElementById("appShell").classList.add("hidden");
  document.getElementById(id).classList.remove("hidden");
}
function showApp() {
  screens.forEach(s => document.getElementById(s).classList.add("hidden"));
  document.getElementById("appShell").classList.remove("hidden");
  document.getElementById("authStatus").innerHTML = `Logged in <a id="logoutLink">Logout</a>`;
  document.getElementById("logoutLink").onclick = logout;
  goToPage("home");
}
function logout() { token = null; safeSet("token", ""); showScreen("welcomeScreen"); }

document.getElementById("welcomeLoginBtn").onclick = () => showScreen("loginScreen");
document.getElementById("welcomeRegisterBtn").onclick = () => showScreen("registerScreen");
document.getElementById("goToRegisterLink").onclick = (e) => { e.preventDefault(); showScreen("registerScreen"); };
document.getElementById("goToLoginLink").onclick = (e) => { e.preventDefault(); showScreen("loginScreen"); };
document.getElementById("forgotPasswordLink").onclick = (e) => { e.preventDefault(); showScreen("forgotScreen"); };
document.getElementById("backToLoginFromForgot").onclick = (e) => { e.preventDefault(); showScreen("loginScreen"); };

// ================= REGISTER =================
document.getElementById("registerSubmitBtn").onclick = async () => {
  const email = document.getElementById("registerEmail").value.trim();
  const password = document.getElementById("registerPassword").value;
  const errorEl = document.getElementById("registerError");
  errorEl.textContent = "";
  if (!email || !password) { errorEl.textContent = "Enter both email and password."; return; }

  try {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) {
      const detail = Array.isArray(data.detail) ? data.detail[0].msg : data.detail;
      throw new Error(detail || "Registration failed");
    }
    pendingVerifyEmail = email;
    document.getElementById("verifyEmailLabel").textContent = `We sent a 6-digit code to ${email}`;
    showScreen("verifyScreen");
  } catch (err) {
    errorEl.textContent = err.message;
  }
};

// ================= VERIFY EMAIL =================
document.getElementById("verifySubmitBtn").onclick = async () => {
  const code = document.getElementById("verifyCode").value.trim();
  const errorEl = document.getElementById("verifyError");
  errorEl.textContent = "";
  try {
    const res = await fetch(`${API_BASE}/auth/verify-email`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: pendingVerifyEmail, code }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Verification failed");
    token = data.access_token;
    safeSet("token", token);
    showApp();
  } catch (err) {
    errorEl.textContent = err.message;
  }
};

document.getElementById("resendCodeLink").onclick = async (e) => {
  e.preventDefault();
  try {
    await fetch(`${API_BASE}/auth/resend-code`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: pendingVerifyEmail }),
    });
    document.getElementById("verifyError").textContent = "New code sent.";
  } catch (err) {}
};

// ================= LOGIN =================
document.getElementById("loginSubmitBtn").onclick = async () => {
  const email = document.getElementById("loginEmail").value.trim();
  const password = document.getElementById("loginPassword").value;
  const errorEl = document.getElementById("loginError");
  errorEl.textContent = "";
  if (!email || !password) { errorEl.textContent = "Enter both email and password."; return; }

  try {
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form,
    });
    const data = await res.json();
    if (!res.ok) {
      if (res.status === 403) {
        pendingVerifyEmail = email;
        document.getElementById("verifyEmailLabel").textContent = `We sent a 6-digit code to ${email}`;
        showScreen("verifyScreen");
        return;
      }
      throw new Error(data.detail || "Login failed");
    }
    token = data.access_token;
    safeSet("token", token);
    showApp();
  } catch (err) {
    errorEl.textContent = err.message;
  }
};

// ================= FORGOT / RESET PASSWORD =================
document.getElementById("forgotSubmitBtn").onclick = async () => {
  const email = document.getElementById("forgotEmail").value.trim();
  const errorEl = document.getElementById("forgotError");
  errorEl.textContent = "";
  try {
    const res = await fetch(`${API_BASE}/auth/forgot-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Could not send reset code");
    pendingResetEmail = email;
    showScreen("resetScreen");
  } catch (err) {
    errorEl.textContent = err.message;
  }
};

document.getElementById("resetSubmitBtn").onclick = async () => {
  const code = document.getElementById("resetCode").value.trim();
  const newPassword = document.getElementById("resetNewPassword").value;
  const errorEl = document.getElementById("resetError");
  errorEl.textContent = "";
  try {
    const res = await fetch(`${API_BASE}/auth/reset-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: pendingResetEmail, code, new_password: newPassword }),
    });
    const data = await res.json();
    if (!res.ok) {
      const detail = Array.isArray(data.detail) ? data.detail[0].msg : data.detail;
      throw new Error(detail || "Reset failed");
    }
    errorEl.style.color = "var(--accent)";
    errorEl.textContent = "Password reset! Please login.";
    setTimeout(() => { errorEl.style.color = ""; showScreen("loginScreen"); }, 1500);
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

  statusEl.textContent = "Fetching price, checking the other platforms too... this can take up to a minute.";
  try {
    const res = await fetch(`${API_BASE}/products`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify({ url, target_price: targetPrice }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Could not add product");
    statusEl.textContent = `Tracking started — found on ${data.length} site(s).`;
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

  if (currentPage === "dashboard") renderDashboard();
  if (currentPage === "products") renderProductsPage();
}

// ================= HELPERS =================
function groupProducts(products) {
  const groups = {};
  products.forEach(p => {
    const key = p.group_id || `single-${p.id}`;
    if (!groups[key]) groups[key] = [];
    groups[key].push(p);
  });
  return Object.values(groups).map(members => {
    members.sort((a, b) => (a.is_primary === b.is_primary) ? 0 : a.is_primary ? -1 : 1);
    return members;
  });
}

function cheapestInGroup(group) {
  return group.reduce((min, p) => (p.current_price != null && (min.current_price == null || p.current_price < min.current_price)) ? p : min, group[0]);
}

function productCardHTML(group) {
  const main = group[0];
  const cheapest = cheapestInGroup(group);
  const hitTarget = cheapest.current_price != null && cheapest.current_price <= main.target_price;

  const imageHTML = main.image_url
    ? `<img src="${main.image_url}" alt="${main.name}" onerror="this.parentElement.innerHTML='<span class=&quot;no-image&quot;>No image</span>'">`
    : `<span class="no-image">No image</span>`;

  const siteRows = group.map(p => `
    <div class="site-row ${p.id === cheapest.id ? 'cheaper' : ''}" onclick="event.stopPropagation(); openFreshPrice(${p.id}, '${p.url.replace(/'/g, "\\'")}')">
      <span class="site-label">${p.site} ↗</span>
      <span class="price" id="price-${p.id}">${p.current_price != null ? '₹' + p.current_price.toLocaleString() : '—'}</span>
    </div>
  `).join("");

  return `
    <div class="product-card" onclick="loadGroupCharts('${main.group_id}', '${main.name.replace(/'/g, "\\'")}')">
      <div class="image-wrap">${imageHTML}</div>
      <div class="card-body">
        ${main.category ? `<span class="category-tag">${main.category}</span>` : ''}
        <div class="name">${main.name}</div>
        ${siteRows}
        <div class="target-row">
          <span>Target: ₹${main.target_price.toLocaleString()}</span>
          ${hitTarget ? '<span class="badge lowest">Target hit!</span>' : ''}
        </div>
        <button class="btn btn-ghost remove-btn" onclick="event.stopPropagation(); removeProduct(${main.id})">Remove</button>
      </div>
    </div>
  `;
}

async function removeProduct(productId) {
  if (!confirm("Remove this product from tracking?")) return;
  try {
    await fetch(`${API_BASE}/products/${productId}`, {
      method: "DELETE", headers: { "Authorization": `Bearer ${token}` },
    });
    loadProducts();
  } catch (err) {}
}

async function openFreshPrice(productId, url) {
  const priceEl = document.getElementById(`price-${productId}`);
  if (priceEl) priceEl.textContent = "…";
  try {
    const res = await fetch(`${API_BASE}/products/${productId}/refresh`, {
      method: "POST", headers: { "Authorization": `Bearer ${token}` },
    });
    if (res.ok) {
      const updated = await res.json();
      if (priceEl && updated.current_price != null) priceEl.textContent = "₹" + updated.current_price.toLocaleString();
    }
  } catch (e) {}
  window.open(url, "_blank", "noopener");
}

// ================= DASHBOARD =================
function renderDashboard() {
  const groups = groupProducts(allProducts);
  const totalProducts = groups.length;
  const targetsHit = groups.filter(g => { const c = cheapestInGroup(g); return c.current_price != null && c.current_price <= g[0].target_price; }).length;
  const totalCurrent = allProducts.reduce((sum, p) => sum + (p.current_price || 0), 0);
  const totalTarget = allProducts.reduce((sum, p) => sum + (p.target_price || 0), 0);

  document.getElementById("kpiGrid").innerHTML = `
    <div class="kpi-card"><div class="value">${totalProducts}</div><div class="label">Products tracked</div></div>
    <div class="kpi-card"><div class="value">${targetsHit}</div><div class="label">Targets hit</div></div>
    <div class="kpi-card"><div class="value">₹${totalCurrent.toLocaleString()}</div><div class="label">Total current price</div></div>
    <div class="kpi-card"><div class="value">₹${totalTarget.toLocaleString()}</div><div class="label">Total target price</div></div>
  `;

  document.getElementById("dashboardGrid").innerHTML = groups.map(productCardHTML).join("")
    || `<p class="sub">No products yet — add one in the Products page.</p>`;

  drawCategoryPie();
}

// Called when a product card is clicked: shows the bar chart (price by
// site for that product's group), the category pie chart, and the price
// history line chart, all on the Dashboard page.
let lastGroup = [];

async function loadGroupCharts(groupId, name) {
  const group = allProducts.filter(p => p.group_id === groupId);
  if (group.length === 0) return;
  lastGroup = group;

  goToPage("dashboard");
  document.getElementById("chartsWrap").classList.remove("hidden");
  drawSiteBar(group);
  drawCategoryPie();

  const main = group.find(p => p.is_primary) || group[0];
  await showChart(main.id, name);
}

function drawCategoryPie() {
  const counts = {};
  allProducts.forEach(p => { const c = p.category || "Other"; counts[c] = (counts[c] || 0) + 1; });
  const labels = Object.keys(counts);
  const values = Object.values(counts);
  const colors = ["#00D9A3", "#4DA8FF", "#FFB020", "#FF5C6C", "#B57BFF", "#5CE1E6", "#F97316", "#A3E635", "#FB7185", "#38BDF8"];

  if (categoryPieChart) categoryPieChart.destroy();
  const el = document.getElementById("categoryPie");
  if (!el) return;
  categoryPieChart = new Chart(el, {
    type: "doughnut",
    data: { labels, datasets: [{ data: values, backgroundColor: colors, borderWidth: 0 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "right", labels: { color: getComputedStyle(document.body).getPropertyValue("--text-muted") } } } },
  });
}

function drawSiteBar(group) {
  const labels = group.map(p => p.site);
  const values = group.map(p => p.current_price || 0);
  const style = getComputedStyle(document.body);
  const muted = style.getPropertyValue("--text-muted").trim();
  const grid = style.getPropertyValue("--border").trim();

  const titleEl = document.getElementById("barChartTitle");
  if (titleEl) titleEl.textContent = `Price by site — ${group[0].name.slice(0, 30)}`;

  if (siteBarChart) siteBarChart.destroy();
  const el = document.getElementById("siteBarChart");
  if (!el) return;
  siteBarChart = new Chart(el, {
    type: "bar",
    data: { labels, datasets: [{ label: "Price (₹)", data: values, backgroundColor: "#00D9A3" }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { ticks: { color: muted }, grid: { display: false } }, y: { ticks: { color: muted }, grid: { color: grid } } },
    },
  });
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

  const groups = groupProducts(filtered);
  document.getElementById("productsGrid").innerHTML = groups.map(productCardHTML).join("") || `<p class="sub">No products match.</p>`;
}
function setCategory(cat) { activeCategory = cat; renderProductsPage(); }
document.getElementById("searchInput").addEventListener("input", renderProductsPage);

// ================= PRICE HISTORY CHART =================
let lastChartProduct = null;

async function showChart(productId, name) {
  const res = await fetch(`${API_BASE}/products/${productId}`, { headers: { "Authorization": `Bearer ${token}` } });
  if (!res.ok) return;
  const product = await res.json();
  lastChartProduct = { name, product };

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
    data: { labels, datasets: [{ label: "Price (₹)", data: prices, borderColor: accent, backgroundColor: accent + "22", fill: true, tension: 0.3, pointRadius: 2, borderWidth: 2 }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { ticks: { color: muted }, grid: { display: false } }, y: { ticks: { color: muted, callback: v => '₹' + v }, grid: { color: grid } } },
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

  if (data.gender) {
    const radio = document.querySelector(`input[name="gender"][value="${data.gender}"]`);
    if (radio) radio.checked = true;
  }

  const badge = document.getElementById("verifyBadge");
  badge.textContent = data.is_verified ? "Verified" : "Not verified";
  badge.className = "verify-badge " + (data.is_verified ? "verified" : "unverified");

  const picWrap = document.getElementById("profilePicWrap");
  const initial = (data.name || data.email)[0].toUpperCase();
  picWrap.innerHTML = data.profile_picture_url
    ? `<img src="${data.profile_picture_url}" alt="Profile"><div class="pic-edit-overlay">Change</div>`
    : `<span>${initial}</span><div class="pic-edit-overlay">Change</div>`;
  picWrap.onclick = () => document.getElementById("picFileInput").click();
}

document.getElementById("saveSettingsBtn").onclick = async () => {
  const name = document.getElementById("settingsName").value.trim();
  const phone = document.getElementById("settingsPhone").value.trim();
  const ageVal = document.getElementById("settingsAge").value;
  const genderEl = document.querySelector('input[name="gender"]:checked');
  const statusEl = document.getElementById("settingsStatus");
  try {
    const res = await fetch(`${API_BASE}/settings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify({
        name: name || null, phone: phone || null,
        age: ageVal ? parseInt(ageVal) : null,
        gender: genderEl ? genderEl.value : null,
      }),
    });
    if (!res.ok) throw new Error("Could not save settings");
    statusEl.textContent = "Settings saved.";
    loadSettings();
  } catch (err) {
    statusEl.textContent = err.message;
  }
};

document.getElementById("picFileInput").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const statusEl = document.getElementById("settingsStatus");
  const reader = new FileReader();
  reader.onload = async () => {
    try {
      const res = await fetch(`${API_BASE}/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
        body: JSON.stringify({ profile_picture_url: reader.result }),
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
if (token) { showApp(); } else { showScreen("welcomeScreen"); }