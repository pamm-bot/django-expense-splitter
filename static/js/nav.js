(function renderNav() {
  const container = document.getElementById("nav-links");
  if (!container) return;

  if (Api.token()) {
    const username = Api.currentUsername();
    container.innerHTML = `
      <span class="text-muted me-3 mono">${username || "there"}</span>
      <a href="/groups/" class="link-money me-3">Groups</a>
      <button id="logout-btn" class="btn btn-sm btn-outline-light">Log out</button>
    `;
    document.getElementById("logout-btn").addEventListener("click", () => {
      Api.clearToken();
      window.location.href = "/";
    });
  } else {
    container.innerHTML = `<a href="/" class="link-money">Log in</a>`;
  }
})();
