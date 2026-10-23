const $ = (id) => document.getElementById(id);
let currentJobId = null;
let pollTimer = null;
let waPollTimer = null;
let channel = "email";
const drafts = { email: "", whatsapp: "" };
let waDelay = [15, 40];

async function api(url, options = {}) {
  const res = await fetch(url, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

function recipientList() {
  // Phone numbers often contain spaces, so only email lists are split on whitespace.
  const separator = channel === "whatsapp" ? /[\n,;]+/ : /[\s,;]+/;
  return $("recipients").value.split(separator).map((e) => e.trim()).filter(Boolean);
}

function setChannel(next) {
  drafts[channel] = $("recipients").value;
  channel = next;
  $("recipients").value = drafts[channel];
  $("recipients").placeholder = channel === "whatsapp" ? "+91 98765 43210" : "name@example.com";
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.channel === channel));
  document.querySelectorAll(".email-only").forEach((el) => (el.hidden = channel !== "email"));
  document.querySelectorAll(".whatsapp-only").forEach((el) => (el.hidden = channel !== "whatsapp"));
  $("parse-result").textContent = "";
  $("send-error").textContent = "";
  updateCount();
  if (channel === "whatsapp") loadWaStatus();
}

document.querySelectorAll(".tab").forEach((tab) =>
  tab.addEventListener("click", () => setChannel(tab.dataset.channel)));

async function loadWaStatus() {
  clearTimeout(waPollTimer);
  try {
    const s = await api("/api/whatsapp/status");
    waDelay = s.delay;
    const labels = {
      logged_in: `<span class="ok">Connected.</span>`,
      probably_logged_in: `<span class="ok">Connected previously</span> — the session is reused when sending.`,
      starting: "Opening browser…",
      waiting_for_qr: `<strong>Scan the QR code</strong> in the browser window: WhatsApp on your phone → Linked devices → Link a device.`,
      unknown: `<span class="bad">Not connected.</span> Click Connect WhatsApp and scan the QR code.`,
    };
    $("wa-status").innerHTML = (labels[s.status] || `<span class="bad">${escapeHtml(s.detail || s.status)}</span>`) +
      `<br><span class="muted">Limit: ${s.daily_limit} messages/day · ${s.delay[0]}–${s.delay[1]} s between messages</span>`;
    $("wa-login").disabled = ["starting", "waiting_for_qr"].includes(s.status);
    if (["starting", "waiting_for_qr"].includes(s.status)) waPollTimer = setTimeout(loadWaStatus, 2000);
  } catch (e) {
    $("wa-status").textContent = e.message;
  }
}

$("wa-login").addEventListener("click", async () => {
  await api("/api/whatsapp/login", { method: "POST" });
  setTimeout(loadWaStatus, 500);
});

function updateCount() {
  const n = recipientList().length;
  $("recipient-count").textContent = `${n} recipient${n === 1 ? "" : "s"}`;
}

async function loadStatus() {
  try {
    const s = await api("/api/status");
    $("sender-status").innerHTML = s.configured
      ? `Sending from: <strong>${escapeHtml(s.sender)}</strong>`
      : `<span class="bad">No sending account configured — fill in the .env file and restart (see README).</span>`;
  } catch (e) {
    $("sender-status").textContent = e.message;
  }
}

$("recipient-files").addEventListener("change", async (event) => {
  const files = event.target.files;
  if (!files.length) return;
  const form = new FormData();
  for (const f of files) form.append("files", f);
  form.append("channel", channel);
  $("parse-result").textContent = "Reading files…";
  try {
    const result = await api("/api/recipients/parse", { method: "POST", body: form });
    const existing = recipientList();
    const seen = new Set(existing.map((e) => e.toLowerCase()));
    const added = result.emails.filter((e) => !seen.has(e.toLowerCase()));
    $("recipients").value = existing.concat(added).join("\n");
    updateCount();
    const perFile = result.files.map((f) => `${escapeHtml(f.file)}: ${f.found}`).join(", ");
    const noun = channel === "whatsapp" ? "number" : "address";
    let html = `<span class="ok">Added ${added.length} new ${noun}${added.length === 1 ? "" : noun === "number" ? "s" : "es"}</span> (${perFile})`;
    if (result.problems.length) {
      html += `<br><span class="bad">Skipped:</span> ${result.problems.slice(0, 20).map(escapeHtml).join("<br>")}`;
      if (result.problems.length > 20) html += `<br>…and ${result.problems.length - 20} more`;
    }
    $("parse-result").innerHTML = html;
  } catch (e) {
    $("parse-result").innerHTML = `<span class="bad">${escapeHtml(e.message)}</span>`;
  }
  event.target.value = "";
});

$("recipients").addEventListener("input", updateCount);

function composeForm() {
  const form = new FormData();
  form.append("subject", $("subject").value);
  form.append("body", $("body").value);
  form.append("cc", $("cc").value);
  form.append("channel", channel);
  for (const f of $("attachments").files) form.append("attachments", f);
  return form;
}

$("send-test").addEventListener("click", async () => {
  const form = composeForm();
  form.append("to", $("test-to").value);
  $("send-test").disabled = true;
  $("test-result").textContent = "Sending test…";
  try {
    await api("/api/send-test", { method: "POST", body: form });
    $("test-result").innerHTML = `<span class="ok">Test email sent to ${escapeHtml($("test-to").value)}.</span>`;
  } catch (e) {
    $("test-result").innerHTML = `<span class="bad">${escapeHtml(e.message)}</span>`;
  } finally {
    $("send-test").disabled = false;
  }
});

$("review").addEventListener("click", () => {
  $("send-error").textContent = "";
  const recipients = recipientList();
  if (!recipients.length) return ($("send-error").textContent = "Add at least one recipient.");
  const whatsapp = channel === "whatsapp";
  if (!whatsapp && !$("subject").value.trim()) return ($("send-error").textContent = "Subject is required.");
  if (!$("body").value.trim() && !(whatsapp && $("attachments").files.length))
    return ($("send-error").textContent = "Message is required.");
  $("c-count").textContent = `${recipients.length} separate ${whatsapp ? "WhatsApp messages" : "emails"}`;
  if (whatsapp) {
    const minutes = Math.ceil((recipients.length * (waDelay[0] + waDelay[1]) / 2 + recipients.length * 10) / 60);
    $("c-time").textContent = `Estimated time: about ${minutes} minute${minutes === 1 ? "" : "s"}. Keep this computer awake and the WhatsApp browser window open.`;
  } else {
    $("c-time").textContent = "";
  }
  $("c-subject").textContent = $("subject").value;
  $("c-cc").textContent = $("cc").value || "—";
  $("c-attachments").textContent = [...$("attachments").files].map((f) => f.name).join(", ") || "—";
  $("c-body").textContent = $("body").value;
  $("confirm-dialog").showModal();
});

$("confirm-cancel").addEventListener("click", () => $("confirm-dialog").close());

$("confirm-send").addEventListener("click", async () => {
  const form = composeForm();
  form.append("recipients", recipientList().join("\n"));
  $("confirm-send").disabled = true;
  try {
    const { job_id } = await api("/api/jobs", { method: "POST", body: form });
    $("confirm-dialog").close();
    showJob(job_id);
  } catch (e) {
    $("confirm-dialog").close();
    $("send-error").textContent = e.message;
  } finally {
    $("confirm-send").disabled = false;
  }
});

function showJob(jobId) {
  currentJobId = jobId;
  $("job-section").hidden = false;
  $("job-section").scrollIntoView({ behavior: "smooth" });
  refreshJob();
}

async function refreshJob() {
  clearTimeout(pollTimer);
  if (currentJobId == null) return;
  const job = await api(`/api/jobs/${currentJobId}`);
  const c = job.counts;
  const done = c.sent + c.failed;
  $("job-title").textContent = `Job #${job.id} — ${job.subject}`;
  $("progress-bar").style.width = c.total ? `${(done / c.total) * 100}%` : "0";
  $("job-summary").innerHTML =
    `<strong>${job.status}</strong> · ${c.sent} sent · ${c.failed} failed · ${c.pending} waiting · ${c.total} total`;
  $("job-error").textContent = job.error || "";
  $("cancel-job").hidden = job.status !== "running";
  $("retry-job").hidden = job.status === "running" || (c.failed === 0 && c.pending === 0);
  $("job-recipients").innerHTML = job.recipients.map((r) => `
    <tr>
      <td>${escapeHtml(r.address)}</td>
      <td class="${r.status === "sent" ? "ok" : r.status === "failed" ? "bad" : ""}">${r.status}</td>
      <td>${escapeHtml(r.error || r.sent_at || "")}</td>
    </tr>`).join("");
  loadHistory();
  if (job.status === "running") pollTimer = setTimeout(refreshJob, 2000);
}

$("cancel-job").addEventListener("click", async () => {
  await api(`/api/jobs/${currentJobId}/cancel`, { method: "POST" });
  refreshJob();
});

$("retry-job").addEventListener("click", async () => {
  await api(`/api/jobs/${currentJobId}/retry`, { method: "POST" });
  refreshJob();
});

async function loadHistory() {
  const jobs = await api("/api/jobs");
  $("history").innerHTML = jobs.map((j) => `
    <tr data-id="${j.id}">
      <td>${j.id}</td>
      <td>${escapeHtml(j.created_at.replace("T", " "))}</td>
      <td>${j.channel === "whatsapp" ? "WhatsApp" : "Email"}</td>
      <td>${escapeHtml(j.subject)}</td>
      <td>${j.counts.sent}/${j.counts.total}</td>
      <td>${j.counts.failed}</td>
      <td>${j.status}</td>
    </tr>`).join("") || `<tr><td colspan="7" class="muted">No jobs yet</td></tr>`;
}

$("history").addEventListener("click", (event) => {
  const row = event.target.closest("tr[data-id]");
  if (row) showJob(Number(row.dataset.id));
});

loadStatus();
loadHistory();
