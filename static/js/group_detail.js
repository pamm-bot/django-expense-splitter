// Group detail page: members, expenses, balances and settle-up.
if (!Api.token()) window.location.href = "/";

const groupId = document.getElementById("group-name").dataset.groupId;
let currentGroup = null;

async function loadGroup() {
  currentGroup = await Api.getGroup(groupId);
  document.getElementById("group-name").textContent = currentGroup.name;

  document.getElementById("members-list").innerHTML = currentGroup.members
    .map((m) => `<li>${escapeHtml(m.username)}</li>`)
    .join("");

  const payToSelect = document.querySelector('select[name="paid_to"]');
  payToSelect.innerHTML = '<option value="" disabled selected>Pay to...</option>' + currentGroup.members
    .filter((m) => m.username !== Api.currentUsername())
    .map((m) => `<option value="${escapeHtml(m.username)}">${escapeHtml(m.username)}</option>`)
    .join("");

  document.getElementById("split-members").innerHTML = currentGroup.members.map((m) => `
    <div class="form-check">
      <input class="form-check-input" type="checkbox" value="${escapeHtml(m.username)}" id="split-${m.id}" checked>
      <label class="form-check-label" for="split-${m.id}">${escapeHtml(m.username)}</label>
    </div>
  `).join("");

  const deleteBtn = document.getElementById("delete-group-btn");
  if (currentGroup.created_by.username === Api.currentUsername()) {
    deleteBtn.classList.remove("d-none");
  }
}

async function loadExpenses() {
  const expenses = await Api.listExpenses(groupId);
  const list = document.getElementById("expenses-list");

  if (expenses.length === 0) {
    list.innerHTML = `<li class="list-group-item text-muted">No expenses yet.</li>`;
    return;
  }

  list.innerHTML = expenses.slice().reverse().map((expense) => `
    <li class="list-group-item d-flex justify-content-between align-items-center" data-expense-id="${expense.id}">
      <div>
        <strong>${escapeHtml(expense.description)}</strong>
        <div class="small text-muted">Paid by ${escapeHtml(expense.paid_by.username)}</div>
      </div>
      <div class="d-flex align-items-center gap-3">
        <span class="amount">€${expense.amount}</span>
        <button type="button" class="btn btn-sm btn-outline-danger delete-expense-btn" data-expense-id="${expense.id}" aria-label="Delete expense">&times;</button>
      </div>
    </li>
  `).join("");

  list.querySelectorAll(".delete-expense-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("Delete this expense?")) return;
      try {
        await Api.deleteExpense(groupId, btn.dataset.expenseId);
        loadExpenses();
        loadBalances();
      } catch (err) {
        alert(err.message);
      }
    });
  });
}

async function loadBalances() {
  const { balances, suggested_settlements } = await Api.getBalances(groupId);
  const list = document.getElementById("balances-list");

  if (balances.length === 0) {
    list.innerHTML = `<li class="text-muted small">All settled up!</li>`;
  } else {
    list.innerHTML = balances.map((entry) => {
      const positive = parseFloat(entry.amount) > 0;
      const label = positive ? "is owed" : "owes";
      return `<li>${escapeHtml(entry.user.username)} <span class="amount ${positive ? "balance-positive" : "balance-negative"}">${label} €${Math.abs(parseFloat(entry.amount)).toFixed(2)}</span></li>`;
    }).join("");
  }

  const suggestions = document.getElementById("settlements-suggestions");
  if (suggested_settlements.length > 0) {
    suggestions.innerHTML = `<small class="text-muted d-block mb-1">Suggested:</small>` + suggested_settlements.map((txn) =>
      `<div class="small mono">${escapeHtml(txn.from.username)} → ${escapeHtml(txn.to.username)}: €${txn.amount}</div>`
    ).join("");
  } else {
    suggestions.innerHTML = "";
  }
}

document.getElementById("add-member-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  try {
    await Api.addMember(groupId, form.get("username"));
    e.target.reset();
    loadGroup();
  } catch (err) {
    alert(err.message);
  }
});

document.getElementById("add-expense-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const errorBox = document.getElementById("expense-error");
  errorBox.textContent = "";

  const splitAmong = Array.from(document.querySelectorAll('#split-members input:checked')).map((el) => el.value);

  try {
    await Api.createExpense(groupId, {
      description: form.get("description"),
      amount: form.get("amount"),
      split_equally_among: splitAmong,
    });
    e.target.reset();
    loadExpenses();
    loadBalances();
  } catch (err) {
    errorBox.textContent = err.message;
  }
});

document.getElementById("settle-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  try {
    await Api.createSettlement(groupId, { paid_to: form.get("paid_to"), amount: form.get("amount") });
    e.target.reset();
    loadBalances();
  } catch (err) {
    alert(err.message);
  }
});

document.getElementById("delete-group-btn").addEventListener("click", async () => {
  if (!confirm("Delete this group and all its expenses?")) return;
  await Api.deleteGroup(groupId);
  window.location.href = "/groups/";
});

loadGroup().then(() => {
  loadExpenses();
  loadBalances();
});
