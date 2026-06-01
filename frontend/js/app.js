const STORAGE_USERS = "scheduler_users";

function apiBase() {
  const input = document.getElementById("apiBase");
  const val = (input?.value || "").trim();
  if (val) return val.replace(/\/$/, "");
  return window.location.origin;
}

function toast(message, type = "success") {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.className = `toast ${type}`;
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.add("hidden"), 4000);
}

async function api(method, path, body) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body !== undefined) opts.body = JSON.stringify(body);

  const res = await fetch(`${apiBase()}${path}`, opts);
  let data = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!res.ok) {
    const detail = data?.detail ?? data ?? res.statusText;
    throw new Error(typeof detail === "object" ? JSON.stringify(detail) : String(detail));
  }
  return data;
}

function loadStoredUsers() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_USERS) || "[]");
  } catch {
    return [];
  }
}

function saveStoredUser(user) {
  const list = loadStoredUsers().filter((u) => u.id !== user.id);
  list.unshift(user);
  localStorage.setItem(STORAGE_USERS, JSON.stringify(list.slice(0, 20)));
  renderStoredUsers();
  populateUserSelects();
}

function renderStoredUsers() {
  const el = document.getElementById("storedUsers");
  const users = loadStoredUsers();
  if (!users.length) {
    el.className = "id-list empty";
    el.textContent = "Create users to see IDs here.";
    return;
  }
  el.className = "id-list";
  el.innerHTML = users
    .map(
      (u) =>
        `<div class="id-chip" data-copy="${u.id}" title="Click to copy ID">${u.full_name} — ${u.email}<br><small>${u.id}</small></div>`
    )
    .join("");
  el.querySelectorAll(".id-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      navigator.clipboard.writeText(chip.dataset.copy);
      toast("Copied user ID");
    });
  });
}

function populateUserSelects() {
  const users = loadStoredUsers();
  const selects = [
    "eventOrganizer",
    "eventParticipants",
    "filterUser",
    "invInvitee",
    "invInvitedBy",
    "invFilterUser",
  ];
  selects.forEach((id) => {
    const sel = document.getElementById(id);
    if (!sel) return;
    const isMulti = sel.multiple;
    const isFilter = id.startsWith("invFilter") || id === "filterUser";
    const current = sel.value;
    sel.innerHTML = isFilter ? '<option value="">All</option>' : '<option value="">— select —</option>';
    users.forEach((u) => {
      const opt = document.createElement("option");
      opt.value = u.id;
      opt.textContent = `${u.full_name} (${u.email})`;
      sel.appendChild(opt);
    });
    if (current) sel.value = current;
    if (isMulti) return;
  });
}

function toIsoDatetimeLocal(value) {
  if (!value) return null;
  return new Date(value).toISOString();
}

function setDefaultDates() {
  const now = new Date();
  const start = new Date(now);
  start.setDate(start.getDate() + ((1 + 7 - start.getDay()) % 7 || 7));
  start.setHours(10, 0, 0, 0);
  const end = new Date(start);
  end.setMinutes(30);

  const fmt = (d) => {
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };

  const startInput = document.querySelector('#formEvent [name="start_time"]');
  const endInput = document.querySelector('#formEvent [name="end_time"]');
  if (startInput && !startInput.value) startInput.value = fmt(start);
  if (endInput && !endInput.value) endInput.value = fmt(end);

  const rangeStart = document.getElementById("rangeStart");
  const rangeEnd = document.getElementById("rangeEnd");
  const rs = new Date(now);
  rs.setDate(1);
  const re = new Date(rs);
  re.setMonth(re.getMonth() + 3);
  if (rangeStart) rangeStart.value = rs.toISOString().slice(0, 10);
  if (rangeEnd) rangeEnd.value = re.toISOString().slice(0, 10);
}

// Tabs
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(`panel-${tab.dataset.tab}`).classList.add("active");
  });
});

document.getElementById("chkRecurring").addEventListener("change", (e) => {
  document.getElementById("recurrenceFields").classList.toggle("hidden", !e.target.checked);
});

document.getElementById("btnHealth").addEventListener("click", async () => {
  const banner = document.getElementById("healthBanner");
  try {
    const data = await api("GET", "/health");
    banner.className = "banner ok";
    banner.textContent = `Healthy — gateway OK (${data.upstream?.user_service || "ok"})`;
    banner.classList.remove("hidden");
  } catch (err) {
    banner.className = "banner err";
    banner.textContent = `Health check failed: ${err.message}`;
    banner.classList.remove("hidden");
  }
});

// Users
document.getElementById("formUser").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  try {
    const user = await api("POST", "/api/v1/users", {
      email: fd.get("email"),
      full_name: fd.get("full_name"),
    });
    saveStoredUser(user);
    toast(`User created: ${user.full_name}`);
    e.target.reset();
    loadUsers();
  } catch (err) {
    toast(err.message, "error");
  }
});

async function loadUsers() {
  const el = document.getElementById("usersList");
  el.innerHTML = "<p class='hint'>Loading…</p>";
  try {
    const data = await api("GET", "/api/v1/users?limit=50");
    data.items.forEach((u) => saveStoredUser(u));
    if (!data.items.length) {
      el.innerHTML = "<p class='hint'>No users yet.</p>";
      return;
    }
    el.innerHTML = data.items
      .map(
        (u) => `
      <div class="item">
        <strong>${u.full_name}</strong> — ${u.email}
        <div class="meta">ID: ${u.id}</div>
      </div>`
      )
      .join("");
  } catch (err) {
    el.innerHTML = `<p class="hint" style="color:var(--danger)">${err.message}</p>`;
  }
}

document.getElementById("btnRefreshUsers").addEventListener("click", loadUsers);

// Events
document.getElementById("formEvent").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const participantSelect = document.getElementById("eventParticipants");
  const participant_ids = [...participantSelect.selectedOptions].map((o) => o.value);

  const body = {
    title: fd.get("title"),
    description: fd.get("description") || null,
    organizer_id: fd.get("organizer_id"),
    start_time: toIsoDatetimeLocal(fd.get("start_time")),
    end_time: toIsoDatetimeLocal(fd.get("end_time")),
    timezone: fd.get("timezone") || "UTC",
    location: fd.get("location") || null,
    participant_ids,
  };

  if (document.getElementById("chkRecurring").checked) {
    const weekdays = [...document.querySelectorAll('[name="by_weekday"] option:checked')].map(
      (o) => o.value
    );
    const monthdayRaw = fd.get("by_monthday");
    const rule = {
      frequency: fd.get("frequency"),
      interval: parseInt(fd.get("interval"), 10) || 1,
      count: parseInt(fd.get("count"), 10) || 10,
    };
    if (weekdays.length) rule.by_weekday = weekdays;
    if (monthdayRaw) {
      rule.by_monthday = monthdayRaw.split(",").map((s) => parseInt(s.trim(), 10)).filter(Boolean);
    }
    body.recurrence_rule = rule;
  }

  try {
    const event = await api("POST", "/api/v1/events", body);
    toast(`Event created: ${event.title}`);
    document.getElementById("invEventId").value = event.id;
    document.getElementById("occSeriesId").value = event.id;
    loadEvents();
  } catch (err) {
    toast(err.message, "error");
  }
});

async function loadEvents() {
  const el = document.getElementById("eventsList");
  const rs = document.getElementById("rangeStart").value;
  const re = document.getElementById("rangeEnd").value;
  const userId = document.getElementById("filterUser").value;

  if (!rs || !re) {
    toast("Set date range", "error");
    return;
  }

  const rangeStart = new Date(rs).toISOString();
  const rangeEnd = new Date(re);
  rangeEnd.setHours(23, 59, 59, 999);
  let path = `/api/v1/events?range_start=${encodeURIComponent(rangeStart)}&range_end=${encodeURIComponent(rangeEnd.toISOString())}&limit=100`;
  if (userId) path += `&user_id=${userId}`;

  el.innerHTML = "<p class='hint'>Loading…</p>";
  try {
    const data = await api("GET", path);
    if (!data.items.length) {
      el.innerHTML = "<p class='hint'>No events in this range.</p>";
      return;
    }
    el.innerHTML = data.items
      .map((ev) => {
        const start = new Date(ev.start_time).toLocaleString();
        const end = new Date(ev.end_time).toLocaleString();
        const badges = [
          ev.is_recurring ? "recurring" : "one-time",
          ev.is_exception ? "exception" : "",
        ]
          .filter(Boolean)
          .map((b) => `<span class="badge ${b === "exception" ? "exception" : "pending"}">${b}</span>`)
          .join(" ");
        return `
        <div class="item">
          <strong>${ev.title}</strong> ${badges}
          <div class="meta">${start} → ${end} · ${ev.timezone}${ev.location ? " · " + ev.location : ""}</div>
          <div class="meta">Series: ${ev.series_id} · Occurrence: ${ev.original_start}</div>
          <div class="actions">
            <button type="button" class="btn secondary btn-fill-occ" data-series="${ev.series_id}" data-start="${ev.original_start}">Use in edit form</button>
            <button type="button" class="btn secondary btn-fill-inv" data-series="${ev.series_id}">Use for invitation</button>
          </div>
        </div>`;
      })
      .join("");

    el.querySelectorAll(".btn-fill-occ").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.getElementById("occSeriesId").value = btn.dataset.series;
        document.querySelector('#formOccurrence [name="occurrence_start"]').value = btn.dataset.start;
        toast("Filled occurrence form");
      });
    });
    el.querySelectorAll(".btn-fill-inv").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.getElementById("invEventId").value = btn.dataset.series;
        document.querySelector('[data-tab="invitations"]').click();
        toast("Filled invitation form");
      });
    });
  } catch (err) {
    el.innerHTML = `<p class="hint" style="color:var(--danger)">${err.message}</p>`;
  }
}

document.getElementById("btnLoadEvents").addEventListener("click", loadEvents);

document.getElementById("formOccurrence").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const seriesId = fd.get("series_id");
  const occurrenceStart = fd.get("occurrence_start");
  const scope = fd.get("scope");
  const action = fd.get("action");

  if (!seriesId || !occurrenceStart) {
    toast("Series ID and occurrence start required", "error");
    return;
  }

  try {
    if (action === "delete") {
      await api("DELETE", `/api/v1/events/${seriesId}/occurrences`, {
        scope,
        occurrence_start: occurrenceStart,
      });
      toast("Occurrence deleted / series updated");
    } else {
      const body = { scope, occurrence_start: occurrenceStart };
      if (fd.get("title")) body.title = fd.get("title");
      const st = fd.get("start_time");
      const et = fd.get("end_time");
      if (st) body.start_time = toIsoDatetimeLocal(st);
      if (et) body.end_time = toIsoDatetimeLocal(et);
      await api("PATCH", `/api/v1/events/${seriesId}/occurrences`, body);
      toast("Occurrence updated");
    }
    loadEvents();
  } catch (err) {
    toast(err.message, "error");
  }
});

// Invitations
document.getElementById("formInvitation").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = {
    event_series_id: fd.get("event_series_id"),
    invitee_id: fd.get("invitee_id"),
    invited_by: fd.get("invited_by"),
  };
  const occ = fd.get("occurrence_start");
  if (occ) body.occurrence_start = occ;

  try {
    await api("POST", "/api/v1/invitations", body);
    toast("Invitation sent");
    loadInvitations();
  } catch (err) {
    toast(err.message, "error");
  }
});

async function loadInvitations() {
  const el = document.getElementById("invitationsList");
  const inviteeId = document.getElementById("invFilterUser").value;
  const status = document.getElementById("invFilterStatus").value;

  let path = "/api/v1/invitations?limit=50";
  if (inviteeId) path += `&invitee_id=${inviteeId}`;
  if (status) path += `&status=${status}`;

  el.innerHTML = "<p class='hint'>Loading…</p>";
  try {
    const data = await api("GET", path);
    if (!data.items.length) {
      el.innerHTML = "<p class='hint'>No invitations.</p>";
      return;
    }
    el.innerHTML = data.items
      .map(
        (inv) => `
      <div class="item">
        <span class="badge ${inv.status}">${inv.status}</span>
        <strong style="margin-left:0.5rem">Event ${inv.event_series_id.slice(0, 8)}…</strong>
        <div class="meta">Invitation: ${inv.id} · Invitee: ${inv.invitee_id}</div>
        ${inv.status === "pending" ? `
        <div class="actions">
          <button type="button" class="btn success btn-rsvp" data-id="${inv.id}" data-status="accepted">Accept</button>
          <button type="button" class="btn warn btn-rsvp" data-id="${inv.id}" data-status="tentative">Tentative</button>
          <button type="button" class="btn danger btn-rsvp" data-id="${inv.id}" data-status="rejected">Reject</button>
        </div>` : ""}
      </div>`
      )
      .join("");

    el.querySelectorAll(".btn-rsvp").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          await api("PATCH", `/api/v1/invitations/${btn.dataset.id}/status`, {
            status: btn.dataset.status,
          });
          toast(`Marked as ${btn.dataset.status}`);
          loadInvitations();
        } catch (err) {
          toast(err.message, "error");
        }
      });
    });
  } catch (err) {
    el.innerHTML = `<p class="hint" style="color:var(--danger)">${err.message}</p>`;
  }
}

document.getElementById("btnLoadInvitations").addEventListener("click", loadInvitations);

// Init
document.getElementById("apiBase").value = window.location.origin;
setDefaultDates();
renderStoredUsers();
populateUserSelects();
loadUsers();
