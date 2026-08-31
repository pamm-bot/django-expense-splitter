// Set a new password from an emailed reset link. The uid/token come from
// data attributes on the form, which the template fills in from the URL.
const form = document.getElementById("reset-confirm-form");
const uid = form.dataset.uid;
const token = form.dataset.token;

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const data = new FormData(e.target);
  const messageBox = document.getElementById("reset-confirm-message");
  try {
    await Api.confirmPasswordReset(uid, token, data.get("password"));
    messageBox.className = "small mb-2 balance-positive";
    messageBox.textContent = "Password updated — you can now log in.";
    e.target.reset();
    setTimeout(() => { window.location.href = "/"; }, 1500);
  } catch (err) {
    messageBox.className = "small mb-2 text-danger";
    messageBox.textContent = err.message;
  }
});
