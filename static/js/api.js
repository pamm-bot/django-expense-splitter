// Escapes user-provided text before it's dropped into innerHTML.
function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

// Thin fetch wrapper around the JSON API. Every frontend page talks to the
// backend exclusively through this — nothing here has access to the
// database directly, same as any external API consumer would.
const Api = {
  base: "/api",

  token() {
    return localStorage.getItem("token");
  },

  setToken(token) {
    localStorage.setItem("token", token);
  },

  clearToken() {
    localStorage.removeItem("token");
  },

  currentUsername() {
    return localStorage.getItem("username");
  },

  setCurrentUsername(username) {
    localStorage.setItem("username", username);
  },

  async request(path, { method = "GET", body } = {}) {
    const headers = { "Content-Type": "application/json" };
    const token = this.token();
    if (token) headers["Authorization"] = `Token ${token}`;

    const response = await fetch(`${this.base}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const message = typeof data === "object" ? Object.values(data).flat().join(" ") : "Something went wrong.";
      throw new Error(message || "Something went wrong.");
    }

    return data;
  },

  register(username, email, password) {
    return this.request("/auth/register/", { method: "POST", body: { username, email, password } });
  },

  login(username, password) {
    return this.request("/auth/login/", { method: "POST", body: { username, password } });
  },

  requestPasswordReset(email) {
    return this.request("/auth/password-reset/", { method: "POST", body: { email } });
  },

  confirmPasswordReset(uid, token, password) {
    return this.request("/auth/password-reset/confirm/", { method: "POST", body: { uid, token, password } });
  },

  // List endpoints are paginated (DRF PageNumberPagination); the pages here
  // are always well under PAGE_SIZE, so just hand back the results array.
  async listGroups() {
    const data = await this.request("/groups/");
    return data.results ?? data;
  },

  createGroup(name) {
    return this.request("/groups/", { method: "POST", body: { name } });
  },

  getGroup(groupId) {
    return this.request(`/groups/${groupId}/`);
  },

  deleteGroup(groupId) {
    return this.request(`/groups/${groupId}/`, { method: "DELETE" });
  },

  addMember(groupId, username) {
    return this.request(`/groups/${groupId}/members/`, { method: "POST", body: { username } });
  },

  async listExpenses(groupId) {
    const data = await this.request(`/groups/${groupId}/expenses/`);
    return data.results ?? data;
  },

  createExpense(groupId, payload) {
    return this.request(`/groups/${groupId}/expenses/`, { method: "POST", body: payload });
  },

  deleteExpense(groupId, expenseId) {
    return this.request(`/groups/${groupId}/expenses/${expenseId}/`, { method: "DELETE" });
  },

  getBalances(groupId) {
    return this.request(`/groups/${groupId}/balances/`);
  },

  createSettlement(groupId, payload) {
    return this.request(`/groups/${groupId}/settlements/`, { method: "POST", body: payload });
  },
};
