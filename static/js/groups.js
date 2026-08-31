// Group list page.
if (!Api.token()) window.location.href = "/";

async function loadGroups() {
  const groups = await Api.listGroups();
  const list = document.getElementById("groups-list");

  if (groups.length === 0) {
    list.innerHTML = `<p class="text-muted">No groups yet — create one above.</p>`;
    return;
  }

  list.innerHTML = groups.map((group) => `
    <a href="/groups/${group.id}/" class="group-row">
      <span class="fw-bold">${escapeHtml(group.name)}</span>
      <span class="text-muted mono small">${group.members.length} member${group.members.length === 1 ? "" : "s"}</span>
    </a>
  `).join("");
}

document.getElementById("create-group-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  await Api.createGroup(form.get("name"));
  e.target.reset();
  loadGroups();
});

loadGroups();
