// Request a password-reset email.
document.getElementById("reset-request-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const messageBox = document.getElementById("reset-message");
  try {
    const { detail } = await Api.requestPasswordReset(form.get("email"));
    messageBox.className = "small mb-2 balance-positive";
    messageBox.textContent = detail;
    e.target.reset();
  } catch (err) {
    messageBox.className = "small mb-2 text-danger";
    messageBox.textContent = err.message;
  }
});
