// ============================================================
// PRICELENS FRONTEND
// ============================================================

// Backend URL
const API_BASE =
  "https://pricelens-backend-0ipu.onrender.com";


// ============================================================
// GLOBAL STATE
// ============================================================

let token = safeGet("token");

let allProducts = [];

let activeCategory = "All";

let currentPage = "home";

let priceChart = null;
let categoryPieChart = null;
let siteBarChart = null;

let pendingVerifyEmail = "";
let pendingResetEmail = "";

let lastGroup = [];
let lastChartProduct = null;


// ============================================================
// LOCAL STORAGE HELPERS
// ============================================================

function safeGet(key) {
  try {
    return localStorage.getItem(key);
  } catch (e) {
    return null;
  }
}


function safeSet(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch (e) {}
}


function safeRemove(key) {
  try {
    localStorage.removeItem(key);
  } catch (e) {}
}


// ============================================================
// THEME
// ============================================================

// ================= THEME =================

const themeToggle = document.getElementById("themeToggle");

function applyTheme(theme) {
    document.body.setAttribute("data-theme", theme);
    safeSet("theme", theme);

    // Theme toggle button exists only if added to HTML
    if (themeToggle) {
        const knob = themeToggle.querySelector(".knob");

        if (knob) {
            knob.textContent = theme === "dark" ? "☾" : "☀";
        }
    }
}

applyTheme(safeGet("theme") || "light");

if (themeToggle) {
    themeToggle.onclick = () => {
        const current =
            document.body.getAttribute("data-theme") || "light";

        const next = current === "dark" ? "light" : "dark";

        applyTheme(next);

        if (currentPage === "dashboard") {
            drawChart();
            drawCategoryPie();

            if (siteBarChart) {
                drawSiteBar(lastGroup);
            }
        }
    };
}
// ============================================================
// PASSWORD EYE TOGGLE
// ============================================================

document
  .querySelectorAll(".eye-icon")
  .forEach((icon) => {

    icon.onclick = () => {

      const input =
        document.getElementById(
          icon.dataset.target
        );

      if (!input) return;

      if (input.type === "password") {

        input.type = "text";

        icon.textContent = "🙈";

      } else {

        input.type = "password";

        icon.textContent = "👁";
      }
    };
  });


// ============================================================
// SCREEN SWITCHING
// ============================================================

const screens = [
  "welcomeScreen",
  "loginScreen",
  "registerScreen",
  "verifyScreen",
  "forgotScreen",
  "resetScreen"
];


function showScreen(id) {

  screens.forEach((screen) => {

    const element =
      document.getElementById(screen);

    if (element) {
      element.classList.add("hidden");
    }
  });


  const appShell =
    document.getElementById("appShell");

  if (appShell) {
    appShell.classList.add("hidden");
  }


  const target =
    document.getElementById(id);

  if (target) {
    target.classList.remove("hidden");
  }
}


// ============================================================
// SHOW APPLICATION
// ============================================================

function showApp(showIntro = true) {

  screens.forEach((screen) => {

    const element =
      document.getElementById(screen);

    if (element) {
      element.classList.add("hidden");
    }
  });


  const appShell =
    document.getElementById("appShell");

  if (!appShell) return;

  appShell.classList.remove("hidden");


  // ----------------------------------------------------------
  // Login status
  // ----------------------------------------------------------

  const authStatus =
    document.getElementById("authStatus");

  if (authStatus) {

    authStatus.innerHTML =
      `Logged in <a id="logoutLink">Logout</a>`;

    const logoutLink =
      document.getElementById("logoutLink");

    if (logoutLink) {
      logoutLink.onclick = logout;
    }
  }


  // ----------------------------------------------------------
  // Show welcome intro after login/register
  // ----------------------------------------------------------

  if (showIntro) {

    showWelcomeAfterLogin();

  } else {

    goToPage("home");
  }
}


// ============================================================
// AFTER LOGIN WELCOME PAGE
// ============================================================

function showWelcomeAfterLogin() {

  const appShell =
    document.getElementById("appShell");

  if (!appShell) return;


  appShell.classList.add(
    "post-login-welcome"
  );


  document
    .querySelectorAll(".view")
    .forEach((view) => {

      view.classList.remove("active");
    });


  let welcome =
    document.getElementById(
      "afterLoginWelcome"
    );


  if (welcome) return;


  welcome =
    document.createElement("div");

  welcome.id =
    "afterLoginWelcome";


  welcome.innerHTML = `

    <div class="after-login-card">

      <div class="after-login-icon">
        ✦
      </div>

      <p class="eyebrow">
        WELCOME TO PRICELENS
      </p>

      <h1>
        You're all set!
      </h1>

      <p>
        Your PriceLens account is ready.
        Start tracking products and discover
        better prices.
      </p>

      <button
        id="continueToHomeBtn"
        class="primary-btn"
      >
        Continue to PriceLens →
      </button>

    </div>

  `;


  appShell.appendChild(welcome);


  const continueBtn =
    document.getElementById(
      "continueToHomeBtn"
    );


  if (continueBtn) {

    continueBtn.onclick = () => {

      welcome.remove();

      appShell.classList.remove(
        "post-login-welcome"
      );

      goToPage("home");
    };
  }
}


// ============================================================
// LOGOUT
// ============================================================

function logout() {

  token = null;

  safeRemove("token");

  allProducts = [];

  currentPage = "home";

  showScreen(
    "welcomeScreen"
  );
}


// ============================================================
// WELCOME BUTTONS
// ============================================================

const welcomeLoginBtn =
  document.getElementById(
    "welcomeLoginBtn"
  );

if (welcomeLoginBtn) {

  welcomeLoginBtn.onclick =
    () => showScreen("loginScreen");
}


const welcomeRegisterBtn =
  document.getElementById(
    "welcomeRegisterBtn"
  );

if (welcomeRegisterBtn) {

  welcomeRegisterBtn.onclick =
    () => showScreen("registerScreen");
}


const goToRegisterLink =
  document.getElementById(
    "goToRegisterLink"
  );

if (goToRegisterLink) {

  goToRegisterLink.onclick = (e) => {

    e.preventDefault();

    showScreen(
      "registerScreen"
    );
  };
}


const goToLoginLink =
  document.getElementById(
    "goToLoginLink"
  );

if (goToLoginLink) {

  goToLoginLink.onclick = (e) => {

    e.preventDefault();

    showScreen(
      "loginScreen"
    );
  };
}


const forgotPasswordLink =
  document.getElementById(
    "forgotPasswordLink"
  );

if (forgotPasswordLink) {

  forgotPasswordLink.onclick = (e) => {

    e.preventDefault();

    showScreen(
      "forgotScreen"
    );
  };
}


const backToLoginFromForgot =
  document.getElementById(
    "backToLoginFromForgot"
  );

if (backToLoginFromForgot) {

  backToLoginFromForgot.onclick =
    (e) => {

      e.preventDefault();

      showScreen(
        "loginScreen"
      );
    };
}


// ============================================================
// REGISTER
// ============================================================

const registerSubmitBtn =
  document.getElementById(
    "registerSubmitBtn"
  );


if (registerSubmitBtn) {

  registerSubmitBtn.onclick =
    async () => {

      const email =
        document
          .getElementById(
            "registerEmail"
          )
          .value
          .trim();


      const password =
        document
          .getElementById(
            "registerPassword"
          )
          .value;


      const errorEl =
        document.getElementById(
          "registerError"
        );


      errorEl.textContent = "";


      if (!email || !password) {

        errorEl.textContent =
          "Enter both email and password.";

        return;
      }


      registerSubmitBtn.disabled = true;

      registerSubmitBtn.textContent =
        "Creating account...";


      try {

        const res =
          await fetch(
            `${API_BASE}/auth/register`,
            {
              method: "POST",

              headers: {
                "Content-Type":
                  "application/json"
              },

              body: JSON.stringify({
                email,
                password
              })
            }
          );


        const data =
          await res.json();


        if (!res.ok) {

          const detail =
            Array.isArray(data.detail)
              ? data.detail[0].msg
              : data.detail;

          throw new Error(
            detail ||
            "Registration failed"
          );
        }


        // ----------------------------------------------------
        // IMPORTANT:
        // Do NOT login automatically.
        // User must verify email first.
        // ----------------------------------------------------

        pendingVerifyEmail =
          email;


        const verifyLabel =
          document.getElementById(
            "verifyEmailLabel"
          );


        if (verifyLabel) {

          verifyLabel.textContent =
            `We sent a 6-digit verification code to ${email}`;
        }


        showScreen(
          "verifyScreen"
        );

      } catch (err) {

        errorEl.textContent =
          err.message;

      } finally {

        registerSubmitBtn.disabled =
          false;

        registerSubmitBtn.textContent =
          "Create Account";
      }
    };
}


// ============================================================
// VERIFY EMAIL
// ============================================================

const verifySubmitBtn =
  document.getElementById(
    "verifySubmitBtn"
  );


if (verifySubmitBtn) {

  verifySubmitBtn.onclick =
    async () => {

      const code =
        document
          .getElementById(
            "verifyCode"
          )
          .value
          .trim();


      const errorEl =
        document.getElementById(
          "verifyError"
        );


      errorEl.textContent = "";


      if (!pendingVerifyEmail) {

        errorEl.textContent =
          "Verification email is missing.";

        return;
      }


      if (!code || code.length !== 6) {

        errorEl.textContent =
          "Enter the 6-digit verification code.";

        return;
      }


      verifySubmitBtn.disabled =
        true;

      verifySubmitBtn.textContent =
        "Verifying...";


      try {

        const res =
          await fetch(
            `${API_BASE}/auth/verify-email`,
            {
              method: "POST",

              headers: {
                "Content-Type":
                  "application/json"
              },

              body: JSON.stringify({
                email:
                  pendingVerifyEmail,

                code
              })
            }
          );


        const data =
          await res.json();


        if (!res.ok) {

          throw new Error(
            data.detail ||
            "Verification failed"
          );
        }


        token =
          data.access_token;


        safeSet(
          "token",
          token
        );


        // Clear pending email

        pendingVerifyEmail = "";


        // Show welcome page

        showApp(true);

      } catch (err) {

        errorEl.textContent =
          err.message;

      } finally {

        verifySubmitBtn.disabled =
          false;

        verifySubmitBtn.textContent =
          "Verify Email";
      }
    };
}


// ============================================================
// RESEND VERIFICATION CODE
// ============================================================

const resendCodeLink =
  document.getElementById(
    "resendCodeLink"
  );


if (resendCodeLink) {

  resendCodeLink.onclick =
    async (e) => {

      e.preventDefault();


      const errorEl =
        document.getElementById(
          "verifyError"
        );


      errorEl.textContent =
        "Sending new code...";


      try {

        const res =
          await fetch(
            `${API_BASE}/auth/resend-code`,
            {
              method: "POST",

              headers: {
                "Content-Type":
                  "application/json"
              },

              body: JSON.stringify({
                email:
                  pendingVerifyEmail
              })
            }
          );


        const data =
          await res.json();


        if (!res.ok) {

          throw new Error(
            data.detail ||
            "Could not resend code"
          );
        }


        errorEl.textContent =
          "New verification code sent successfully.";

      } catch (err) {

        errorEl.textContent =
          err.message;
      }
    };
}


// ============================================================
// LOGIN
// ============================================================

const loginSubmitBtn =
  document.getElementById(
    "loginSubmitBtn"
  );


if (loginSubmitBtn) {

  loginSubmitBtn.onclick =
    async () => {

      const email =
        document
          .getElementById(
            "loginEmail"
          )
          .value
          .trim();


      const password =
        document
          .getElementById(
            "loginPassword"
          )
          .value;


      const errorEl =
        document.getElementById(
          "loginError"
        );


      errorEl.textContent = "";


      if (!email || !password) {

        errorEl.textContent =
          "Enter both email and password.";

        return;
      }


      loginSubmitBtn.disabled =
        true;

      loginSubmitBtn.textContent =
        "Logging in...";


      try {

        const form =
          new URLSearchParams();


        form.append(
          "username",
          email
        );


        form.append(
          "password",
          password
        );


        const res =
          await fetch(
            `${API_BASE}/auth/login`,
            {
              method: "POST",

              headers: {
                "Content-Type":
                  "application/x-www-form-urlencoded"
              },

              body: form
            }
          );


        const data =
          await res.json();


        if (!res.ok) {

          // Unverified account

          if (res.status === 403) {

            pendingVerifyEmail =
              email;


            const verifyLabel =
              document.getElementById(
                "verifyEmailLabel"
              );


            if (verifyLabel) {

              verifyLabel.textContent =
                `Please verify your email: ${email}`;
            }


            showScreen(
              "verifyScreen"
            );


            return;
          }


          throw new Error(
            data.detail ||
            "Login failed"
          );
        }


        token =
          data.access_token;


        safeSet(
          "token",
          token
        );


        // Show welcome page after login

        showApp(true);

      } catch (err) {

        errorEl.textContent =
          err.message;

      } finally {

        loginSubmitBtn.disabled =
          false;

        loginSubmitBtn.textContent =
          "Login";
      }
    };
}


// ============================================================
// FORGOT PASSWORD
// ============================================================

const forgotSubmitBtn =
  document.getElementById(
    "forgotSubmitBtn"
  );


if (forgotSubmitBtn) {

  forgotSubmitBtn.onclick =
    async () => {

      const email =
        document
          .getElementById(
            "forgotEmail"
          )
          .value
          .trim();


      const errorEl =
        document.getElementById(
          "forgotError"
        );


      errorEl.textContent = "";


      if (!email) {

        errorEl.textContent =
          "Enter your email.";

        return;
      }


      try {

        const res =
          await fetch(
            `${API_BASE}/auth/forgot-password`,
            {
              method: "POST",

              headers: {
                "Content-Type":
                  "application/json"
              },

              body: JSON.stringify({
                email
              })
            }
          );


        const data =
          await res.json();


        if (!res.ok) {

          throw new Error(
            data.detail ||
            "Could not send reset code"
          );
        }


        pendingResetEmail =
          email;


        showScreen(
          "resetScreen"
        );

      } catch (err) {

        errorEl.textContent =
          err.message;
      }
    };
}


// ============================================================
// RESET PASSWORD
// ============================================================

const resetSubmitBtn =
  document.getElementById(
    "resetSubmitBtn"
  );


if (resetSubmitBtn) {

  resetSubmitBtn.onclick =
    async () => {

      const code =
        document
          .getElementById(
            "resetCode"
          )
          .value
          .trim();


      const newPassword =
        document
          .getElementById(
            "resetNewPassword"
          )
          .value;


      const errorEl =
        document.getElementById(
          "resetError"
        );


      errorEl.textContent = "";


      try {

        const res =
          await fetch(
            `${API_BASE}/auth/reset-password`,
            {
              method: "POST",

              headers: {
                "Content-Type":
                  "application/json"
              },

              body: JSON.stringify({

                email:
                  pendingResetEmail,

                code,

                new_password:
                  newPassword
              })
            }
          );


        const data =
          await res.json();


        if (!res.ok) {

          const detail =
            Array.isArray(data.detail)
              ? data.detail[0].msg
              : data.detail;


          throw new Error(
            detail ||
            "Reset failed"
          );
        }


        errorEl.style.color =
          "var(--accent)";


        errorEl.textContent =
          "Password reset successful! Please login.";


        setTimeout(() => {

          errorEl.style.color = "";

          showScreen(
            "loginScreen"
          );

        }, 1500);

      } catch (err) {

        errorEl.textContent =
          err.message;
      }
    };
}


// ============================================================
// NAVIGATION
// ============================================================

document
  .querySelectorAll(".nav-links button")
  .forEach((btn) => {

    btn.onclick = () => {

      goToPage(
        btn.dataset.page
      );
    };
  });


function goToPage(pageName) {

  currentPage =
    pageName;


  document
    .querySelectorAll(".view")
    .forEach((view) => {

      view.classList.remove(
        "active"
      );
    });


  const target =
    document.getElementById(
      `view-${pageName}`
    );


  if (target) {

    target.classList.add(
      "active"
    );
  }


  document
    .querySelectorAll(
      ".nav-links button"
    )
    .forEach((button) => {

      button.classList.toggle(
        "active",
        button.dataset.page ===
          pageName
      );
    });


  if (pageName === "dashboard") {
    loadProducts();
  }


  if (pageName === "productlist") {
    loadProducts();
  }


  if (pageName === "settings") {
    loadSettings();
  }
}


// ============================================================
// ADD PRODUCT
// ============================================================

const addProductBtn =
  document.getElementById(
    "addProductBtn"
  );


if (addProductBtn) {

  addProductBtn.onclick =
    async () => {

      const url =
        document
          .getElementById(
            "productUrl"
          )
          .value
          .trim();


      const targetPrice =
        parseFloat(
          document
            .getElementById(
              "targetPrice"
            )
            .value
        );


      const statusEl =
        document.getElementById(
          "addProductStatus"
        );


      if (!url || !targetPrice) {

        statusEl.textContent =
          "Enter a product URL and target price.";

        return;
      }


      statusEl.textContent =
        "Checking availability across sites...";


      try {

        const res =
          await fetch(
            `${API_BASE}/products`,
            {
              method: "POST",

              headers: {

                "Content-Type":
                  "application/json",

                "Authorization":
                  `Bearer ${token}`
              },

              body: JSON.stringify({

                url,

                target_price:
                  targetPrice
              })
            }
          );


        const data =
          await res.json();


        if (!res.ok) {

          throw new Error(
            data.detail ||
            "Could not add product"
          );
        }


        statusEl.textContent =
          `Available and now tracking — found on ${data.length} site(s).`;


        document.getElementById(
          "productUrl"
        ).value = "";


        document.getElementById(
          "targetPrice"
        ).value = "";


        allProducts =
          allProducts.concat(
            data
          );


        const groups =
          groupProducts(data);


        const grid =
          document.getElementById(
            "justAddedGrid"
          );


        if (grid) {

          grid.innerHTML =
            groups
              .map(productCardHTML)
              .join("");
        }

      } catch (err) {

        statusEl.textContent =
          err.message;
      }
    };
}


// ============================================================
// LOAD PRODUCTS
// ============================================================

async function loadProducts() {

  if (!token) return;


  try {

    const res =
      await fetch(
        `${API_BASE}/products`,
        {
          headers: {
            "Authorization":
              `Bearer ${token}`
          }
        }
      );


    if (!res.ok) {

      if (res.status === 401) {
        logout();
      }

      return;
    }


    allProducts =
      await res.json();


    if (currentPage === "dashboard") {

      renderDashboard();
    }


    // FIX:
    // productlist and products mismatch corrected

    if (currentPage === "productlist") {

      renderProductsPage();
    }

  } catch (err) {

    console.error(
      "Product loading failed:",
      err
    );
  }
}


// ============================================================
// GROUP PRODUCTS
// ============================================================

function groupProducts(products) {

  const groups = {};


  products.forEach((product) => {

    const key =
      product.group_id ||
      `single-${product.id}`;


    if (!groups[key]) {
      groups[key] = [];
    }


    groups[key].push(
      product
    );
  });


  return Object
    .values(groups)
    .map((members) => {

      members.sort(
        (a, b) =>
          a.is_primary ===
          b.is_primary

            ? 0

            : a.is_primary
              ? -1
              : 1
      );


      return members;
    });
}


// ============================================================
// CHEAPEST PRODUCT
// ============================================================

function cheapestInGroup(group) {

  return group.reduce(
    (min, product) => {

      if (
        product.current_price != null &&
        (
          min.current_price == null ||
          product.current_price <
            min.current_price
        )
      ) {
        return product;
      }


      return min;

    },
    group[0]
  );
}


// ============================================================
// PRODUCT CARD
// ============================================================

function productCardHTML(group) {

  const main =
    group[0];


  const cheapest =
    cheapestInGroup(group);


  const hitTarget =
    cheapest.current_price != null &&
    cheapest.current_price <=
      main.target_price;


  const imageHTML =
    main.image_url

      ? `
        <img
          src="${main.image_url}"
          alt="${main.name}"
          onerror="
            this.parentElement.innerHTML =
            '<span class=&quot;no-image&quot;>No image</span>'
          "
        >
      `

      : `
        <span class="no-image">
          No image
        </span>
      `;


  const siteRows =
    group
      .map((product) => `

        <div
          class="
            site-row
            ${product.id === cheapest.id
              ? "cheaper"
              : ""}
          "
          onclick="
            event.stopPropagation();
            openFreshPrice(
              ${product.id},
              '${product.url.replace(
                /'/g,
                "\\'"
              )}'
            )
          "
        >

          <span class="site-label">
            ${product.site} ↗
          </span>

          <span
            class="price"
            id="price-${product.id}"
          >
            ${
              product.current_price != null
                ? "₹" +
                  product.current_price.toLocaleString()
                : "—"
            }
          </span>

        </div>

      `)
      .join("");


  const safeGroupId =
    String(main.group_id || "")
      .replace(/'/g, "\\'");


  const safeName =
    String(main.name || "")
      .replace(/'/g, "\\'");


  return `

    <div
      class="product-card"
      onclick="
        loadGroupCharts(
          '${safeGroupId}',
          '${safeName}'
        )
      "
    >

      <div class="image-wrap">

        ${imageHTML}

      </div>


      <div class="card-body">

        ${
          main.category
            ? `
              <span class="category-tag">
                ${main.category}
              </span>
            `
            : ""
        }


        <div class="name">
          ${main.name}
        </div>


        ${siteRows}


        <div class="target-row">

          <span>
            Target:
            ₹${main.target_price.toLocaleString()}
          </span>


          ${
            hitTarget
              ? `
                <span class="badge lowest">
                  Target hit!
                </span>
              `
              : ""
          }

        </div>


        <button
          class="btn btn-ghost remove-btn"
          onclick="
            event.stopPropagation();
            removeProduct(${main.id})
          "
        >
          Remove
        </button>

      </div>

    </div>

  `;
}


// ============================================================
// REMOVE PRODUCT
// ============================================================

async function removeProduct(productId) {

  if (
    !confirm(
      "Remove this product from tracking?"
    )
  ) {
    return;
  }


  try {

    const res =
      await fetch(
        `${API_BASE}/products/${productId}`,
        {
          method: "DELETE",

          headers: {
            "Authorization":
              `Bearer ${token}`
          }
        }
      );


    if (!res.ok) {

      throw new Error(
        "Could not remove product"
      );
    }


    await loadProducts();

  } catch (err) {

    console.error(
      err
    );
  }
}


// ============================================================
// REFRESH PRODUCT
// ============================================================

async function openFreshPrice(
  productId,
  url
) {

  const priceEl =
    document.getElementById(
      `price-${productId}`
    );


  if (priceEl) {

    priceEl.textContent =
      "…";
  }


  try {

    const res =
      await fetch(
        `${API_BASE}/products/${productId}/refresh`,
        {
          method: "POST",

          headers: {
            "Authorization":
              `Bearer ${token}`
          }
        }
      );


    if (res.ok) {

      const updated =
        await res.json();


      if (
        priceEl &&
        updated.current_price != null
      ) {

        priceEl.textContent =
          "₹" +
          updated.current_price
            .toLocaleString();
      }
    }

  } catch (e) {

    console.error(
      e
    );
  }


  window.open(
    url,
    "_blank",
    "noopener"
  );
}


// ============================================================
// DASHBOARD
// ============================================================

function renderDashboard() {

  const groups =
    groupProducts(
      allProducts
    );


  const totalProducts =
    groups.length;


  const targetsHit =
    groups.filter((group) => {

      const cheapest =
        cheapestInGroup(group);


      return (
        cheapest.current_price != null &&
        cheapest.current_price <=
          group[0].target_price
      );

    }).length;


  const totalCurrent =
    allProducts.reduce(
      (sum, product) =>
        sum +
        (product.current_price || 0),
      0
    );


  const totalTarget =
    allProducts.reduce(
      (sum, product) =>
        sum +
        (product.target_price || 0),
      0
    );


  const kpiGrid =
    document.getElementById(
      "kpiGrid"
    );


  if (kpiGrid) {

    kpiGrid.innerHTML = `

      <div class="kpi-card">

        <div class="value">
          ${totalProducts}
        </div>

        <div class="label">
          Products tracked
        </div>

      </div>


      <div class="kpi-card">

        <div class="value">
          ${targetsHit}
        </div>

        <div class="label">
          Targets hit
        </div>

      </div>


      <div class="kpi-card">

        <div class="value">
          ₹${totalCurrent.toLocaleString()}
        </div>

        <div class="label">
          Total current price
        </div>

      </div>


      <div class="kpi-card">

        <div class="value">
          ₹${totalTarget.toLocaleString()}
        </div>

        <div class="label">
          Total target price
        </div>

      </div>

    `;
  }


  const dashboardGrid =
    document.getElementById(
      "dashboardGrid"
    );


  if (dashboardGrid) {

    dashboardGrid.innerHTML =
      groups
        .map(productCardHTML)
        .join("")
      ||
      `
        <p class="sub">
          No products yet —
          add one in the Products page.
        </p>
      `;
  }


  drawCategoryPie();


  const productsGrid =
    document.getElementById(
      "productsGrid"
    );


  if (productsGrid) {

    productsGrid.innerHTML =
      groups
        .map(productCardHTML)
        .join("")
      ||
      `
        <p class="sub">
          No products match.
        </p>
      `;
  }
}


// ============================================================
// GROUP CHARTS
// ============================================================

async function loadGroupCharts(
  groupId,
  name
) {

  const group =
    allProducts.filter(
      (product) =>
        product.group_id ===
        groupId
    );


  if (group.length === 0) {
    return;
  }


  lastGroup =
    group;


  goToPage(
    "dashboard"
  );


  const chartsWrap =
    document.getElementById(
      "chartsWrap"
    );


  if (chartsWrap) {

    chartsWrap.classList.remove(
      "hidden"
    );
  }


  drawSiteBar(
    group
  );


  drawCategoryPie();


  const main =
    group.find(
      (product) =>
        product.is_primary
    ) ||
    group[0];


  await showChart(
    main.id,
    name
  );
}


// ============================================================
// CATEGORY PIE CHART
// ============================================================

function drawCategoryPie() {

  const counts = {};


  allProducts.forEach(
    (product) => {

      const category =
        product.category ||
        "Other";


      counts[category] =
        (counts[category] || 0) +
        1;
    }
  );


  const labels =
    Object.keys(
      counts
    );


  const values =
    Object.values(
      counts
    );


  const colors = [
    "#A78BFA",
    "#8B5CF6",
    "#C4B5FD",
    "#DDD6FE",
    "#7C3AED",
    "#6D28D9",
    "#EDE9FE",
    "#5B21B6"
  ];


  if (categoryPieChart) {

    categoryPieChart.destroy();
  }


  const el =
    document.getElementById(
      "categoryPie"
    );


  if (!el) return;


  categoryPieChart =
    new Chart(
      el,
      {
        type: "doughnut",

        data: {

          labels,

          datasets: [

            {
              data: values,

              backgroundColor:
                colors,

              borderWidth: 0
            }

          ]
        },

        options: {

          responsive: true,

          maintainAspectRatio:
            false,

          plugins: {

            legend: {

              position: "right",

              labels: {

                color:
                  getComputedStyle(
                    document.body
                  )
                    .getPropertyValue(
                      "--text-muted"
                    )
              }
            }
          }
        }
      }
    );
}


// ============================================================
// SITE BAR CHART
// ============================================================

function drawSiteBar(group) {

  if (!group || group.length === 0) {
    return;
  }


  const labels =
    group.map(
      (product) =>
        product.site
    );


  const values =
    group.map(
      (product) =>
        product.current_price || 0
    );


  const style =
    getComputedStyle(
      document.body
    );


  const muted =
    style
      .getPropertyValue(
        "--text-muted"
      )
      .trim();


  const grid =
    style
      .getPropertyValue(
        "--border"
      )
      .trim();


  const titleEl =
    document.getElementById(
      "barChartTitle"
    );


  if (titleEl) {

    titleEl.textContent =
      `Price by site — ${group[0].name.slice(
        0,
        30
      )}`;
  }


  if (siteBarChart) {

    siteBarChart.destroy();
  }


  const el =
    document.getElementById(
      "siteBarChart"
    );


  if (!el) return;


  siteBarChart =
    new Chart(
      el,
      {
        type: "bar",

        data: {

          labels,

          datasets: [

            {
              label:
                "Price (₹)",

              data:
                values,

              backgroundColor:
                "#A78BFA"
            }

          ]
        },

        options: {

          responsive: true,

          maintainAspectRatio:
            false,

          plugins: {

            legend: {
              display: false
            }
          },

          scales: {

            x: {

              ticks: {
                color: muted
              },

              grid: {
                display: false
              }
            },

            y: {

              ticks: {
                color: muted
              },

              grid: {
                color: grid
              }
            }
          }
        }
      }
    );
}


// ============================================================
// PRODUCTS PAGE
// ============================================================

function renderProductsPage() {

  const categories = [
    "All",
    ...new Set(
      allProducts.map(
        (product) =>
          product.category ||
          "Other"
      )
    )
  ];


  const categoryChips =
    document.getElementById(
      "categoryChips"
    );


  if (categoryChips) {

    categoryChips.innerHTML =
      categories
        .map(
          (category) => `

            <div
              class="
                chip
                ${
                  category ===
                  activeCategory
                    ? "active"
                    : ""
                }
              "
              onclick="
                setCategory(
                  '${category.replace(
                    /'/g,
                    "\\'"
                  )}'
                )
              "
            >
              ${category}
            </div>

          `
        )
        .join("");
  }


  const searchInput =
    document.getElementById(
      "searchInput"
    );


  const query =
    (
      searchInput
        ? searchInput.value
        : ""
    )
      .toLowerCase();


  let filtered =
    activeCategory === "All"

      ? allProducts

      : allProducts.filter(
          (product) =>
            (
              product.category ||
              "Other"
            ) ===
            activeCategory
        );


  filtered =
    filtered.filter(
      (product) =>
        product.name
          .toLowerCase()
          .includes(query)
    );


  const groups =
    groupProducts(
      filtered
    );


  const productsGrid =
    document.getElementById(
      "productsGrid"
    );


  if (productsGrid) {

    productsGrid.innerHTML =
      groups
        .map(productCardHTML)
        .join("")
      ||
      `
        <p class="sub">
          No products match.
        </p>
      `;
  }
}


// ============================================================
// CATEGORY FILTER
// ============================================================

function setCategory(category) {

  activeCategory =
    category;

  renderProductsPage();
}


const searchInput =
  document.getElementById(
    "searchInput"
  );


if (searchInput) {

  searchInput.addEventListener(
    "input",
    renderProductsPage
  );
}


// ============================================================
// PRICE HISTORY CHART
// ============================================================

async function showChart(
  productId,
  name
) {

  try {

    const res =
      await fetch(
        `${API_BASE}/products/${productId}`,
        {
          headers: {
            "Authorization":
              `Bearer ${token}`
          }
        }
      );


    if (!res.ok) return;


    const product =
      await res.json();


    lastChartProduct = {
      name,
      product
    };


    const chartSection =
      document.getElementById(
        "chartSection"
      );


    if (chartSection) {

      chartSection.classList.remove(
        "hidden"
      );
    }


    const chartTitle =
      document.getElementById(
        "chartTitle"
      );


    if (chartTitle) {

      chartTitle.textContent =
        `Price history — ${name}`;
    }


    drawChart();


    if (chartSection) {

      chartSection.scrollIntoView({
        behavior: "smooth"
      });
    }

  } catch (err) {

    console.error(
      "Chart loading failed:",
      err
    );
  }
}


// ============================================================
// DRAW PRICE CHART
// ============================================================

function drawChart() {

  if (!lastChartProduct) {
    return;
  }


  const {
    product
  } =
    lastChartProduct;


  const style =
    getComputedStyle(
      document.body
    );


  const accent =
    style
      .getPropertyValue(
        "--accent"
      )
      .trim();


  const muted =
    style
      .getPropertyValue(
        "--text-muted"
      )
      .trim();


  const grid =
    style
      .getPropertyValue(
        "--border"
      )
      .trim();


  const labels =
    product.price_history.map(
      (history) =>
        new Date(
          history.checked_at
        )
          .toLocaleDateString()
    );


  const prices =
    product.price_history.map(
      (history) =>
        history.price
    );


  if (priceChart) {

    priceChart.destroy();
  }


  const canvas =
    document.getElementById(
      "priceChart"
    );


  if (!canvas) return;


  priceChart =
    new Chart(
      canvas,
      {
        type: "line",

        data: {

          labels,

          datasets: [

            {
              label:
                "Price (₹)",

              data:
                prices,

              borderColor:
                accent,

              backgroundColor:
                accent + "22",

              fill: true,

              tension: 0.3,

              pointRadius: 2,

              borderWidth: 2
            }

          ]
        },

        options: {

          responsive: true,

          maintainAspectRatio:
            false,

          plugins: {

            legend: {
              display: false
            }
          },

          scales: {

            x: {

              ticks: {
                color: muted
              },

              grid: {
                display: false
              }
            },

            y: {

              ticks: {

                color: muted,

                callback:
                  (value) =>
                    "₹" + value
              },

              grid: {
                color: grid
              }
            }
          }
        }
      }
    );
}


// ============================================================
// SETTINGS
// ============================================================

async function loadSettings() {

  if (!token) return;


  try {

    const res =
      await fetch(
        `${API_BASE}/settings`,
        {
          headers: {
            "Authorization":
              `Bearer ${token}`
          }
        }
      );


    if (!res.ok) return;


    const data =
      await res.json();


    const settingsEmail =
      document.getElementById(
        "settingsEmail"
      );


    if (settingsEmail) {
      settingsEmail.textContent =
        data.email;
    }


    const settingsName =
      document.getElementById(
        "settingsName"
      );


    if (settingsName) {
      settingsName.value =
        data.name || "";
    }


    const settingsPhone =
      document.getElementById(
        "settingsPhone"
      );


    if (settingsPhone) {
      settingsPhone.value =
        data.phone || "";
    }


    const settingsAge =
      document.getElementById(
        "settingsAge"
      );


    if (settingsAge) {
      settingsAge.value =
        data.age || "";
    }


    const profileEmailDisplay =
      document.getElementById(
        "profileEmailDisplay"
      );


    if (profileEmailDisplay) {

      profileEmailDisplay.textContent =
        data.email;
    }


    const profileNameDisplay =
      document.getElementById(
        "profileNameDisplay"
      );


    if (profileNameDisplay) {

      profileNameDisplay.textContent =
        data.name ||
        "Your name";
    }


    // Gender

    if (data.gender) {

      const radio =
        document.querySelector(
          `input[name="gender"][value="${data.gender}"]`
        );


      if (radio) {
        radio.checked = true;
      }
    }


    // Verification badge

    const badge =
      document.getElementById(
        "verifyBadge"
      );


    if (badge) {

      badge.textContent =
        data.is_verified
          ? "Verified"
          : "Not verified";


      badge.className =
        "verify-badge " +
        (
          data.is_verified
            ? "verified"
            : "unverified"
        );
    }


    // Profile image

    const picWrap =
      document.getElementById(
        "profilePicWrap"
      );


    if (picWrap) {

      const initial =
        (
          data.name ||
          data.email ||
          "U"
        )[0]
          .toUpperCase();


      picWrap.innerHTML =
        data.profile_picture_url

          ? `
            <img
              src="${data.profile_picture_url}"
              alt="Profile"
            >

            <div class="pic-edit-overlay">
              Change
            </div>
          `

          : `
            <span>
              ${initial}
            </span>

            <div class="pic-edit-overlay">
              Change
            </div>
          `;


      picWrap.onclick =
        () => {

          const input =
            document.getElementById(
              "picFileInput"
            );


          if (input) {
            input.click();
          }
        };
    }

  } catch (err) {

    console.error(
      "Settings loading failed:",
      err
    );
  }
}


// ============================================================
// SAVE SETTINGS
// ============================================================

const saveSettingsBtn =
  document.getElementById(
    "saveSettingsBtn"
  );


if (saveSettingsBtn) {

  saveSettingsBtn.onclick =
    async () => {

      const name =
        document
          .getElementById(
            "settingsName"
          )
          .value
          .trim();


      const phone =
        document
          .getElementById(
            "settingsPhone"
          )
          .value
          .trim();


      const ageVal =
        document
          .getElementById(
            "settingsAge"
          )
          .value;


      const genderEl =
        document.querySelector(
          'input[name="gender"]:checked'
        );


      const statusEl =
        document.getElementById(
          "settingsStatus"
        );


      try {

        const res =
          await fetch(
            `${API_BASE}/settings`,
            {
              method: "PUT",

              headers: {

                "Content-Type":
                  "application/json",

                "Authorization":
                  `Bearer ${token}`
              },

              body:
                JSON.stringify({

                  name:
                    name || null,

                  phone:
                    phone || null,

                  age:
                    ageVal
                      ? parseInt(ageVal)
                      : null,

                  gender:
                    genderEl
                      ? genderEl.value
                      : null
                })
            }
          );


        if (!res.ok) {

          throw new Error(
            "Could not save settings"
          );
        }


        statusEl.textContent =
          "Settings saved successfully.";


        loadSettings();

      } catch (err) {

        statusEl.textContent =
          err.message;
      }
    };
}


// ============================================================
// PROFILE PICTURE
// ============================================================

const picFileInput =
  document.getElementById(
    "picFileInput"
  );


if (picFileInput) {

  picFileInput.addEventListener(
    "change",
    async (e) => {

      const file =
        e.target.files[0];


      if (!file) return;


      const statusEl =
        document.getElementById(
          "settingsStatus"
        );


      const reader =
        new FileReader();


      reader.onload =
        async () => {

          try {

            const res =
              await fetch(
                `${API_BASE}/settings`,
                {
                  method: "PUT",

                  headers: {

                    "Content-Type":
                      "application/json",

                    "Authorization":
                      `Bearer ${token}`
                  },

                  body:
                    JSON.stringify({

                      profile_picture_url:
                        reader.result
                    })
                }
              );


            if (!res.ok) {

              throw new Error(
                "Could not save photo"
              );
            }


            statusEl.textContent =
              "Profile photo updated.";


            loadSettings();

          } catch (err) {

            statusEl.textContent =
              err.message;
          }
        };


      reader.readAsDataURL(
        file
      );
    }
  );
}


// ============================================================
// SETTINGS LOGOUT
// ============================================================

const logoutBtnSettings =
  document.getElementById(
    "logoutBtnSettings"
  );


if (logoutBtnSettings) {

  logoutBtnSettings.onclick =
    logout;
}


// ============================================================
// BOOT
// ============================================================

// IMPORTANT:
//
// If token already exists, go directly to Home.
// Do NOT show the after-login welcome page
// again after browser refresh.

if (token) {

  showApp(false);

} else {

  showScreen(
    "welcomeScreen"
  );
}