// Login / register page. Redirects to the group list if already signed in.
if (Api.token()) window.location.href = "/groups/";

document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const errorBox = document.getElementById("login-error");
  errorBox.textContent = "";
  try {
    const { token } = await Api.login(form.get("username"), form.get("password"));
    Api.setToken(token);
    Api.setCurrentUsername(form.get("username"));
    window.location.href = "/groups/";
  } catch (err) {
    errorBox.textContent = "Wrong username or password.";
  }
});

document.getElementById("register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const errorBox = document.getElementById("register-error");
  errorBox.textContent = "";
  try {
    await Api.register(form.get("username"), form.get("email"), form.get("password"));
    const { token } = await Api.login(form.get("username"), form.get("password"));
    Api.setToken(token);
    Api.setCurrentUsername(form.get("username"));
    window.location.href = "/groups/";
  } catch (err) {
    errorBox.textContent = err.message;
  }
});
