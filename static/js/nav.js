(function renderNav() {
  const container = document.getElementById("nav-links");
  if (!container) return;

  if (Api.token()) {
    const username = Api.currentUsername();
    container.innerHTML = `
      <span class="text-white me-3">Hi, ${username || "there"}</span>
      <a href="/groups/" class="text-white me-3 text-decoration-none">Groups</a>
      <button id="logout-btn" class="btn btn-sm btn-outline-light">Log out</button>
    `;
    document.getElementById("logout-btn").addEventListener("click", () => {
      Api.clearToken();
      window.location.href = "/";
    });
  } else {
    container.innerHTML = `<a href="/" class="text-white text-decoration-none">Log in</a>`;
  }
})();
