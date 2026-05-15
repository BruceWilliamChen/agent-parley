const POLL_INTERVAL_MS = 2000;
const API_URL = "/api/rooms/main/messages";

const params = new URLSearchParams(window.location.search);
const selfName = params.get("as");

const messagesEl = document.getElementById("messages");
const statusEl = document.getElementById("status");
const roomEl = document.getElementById("room");
const scrollBtn = document.getElementById("scrollBtn");

const identityLabel = selfName ? `viewing as ${selfName}` : "observing";
roomEl.textContent = `agent-parley · main · ${identityLabel}`;

let sinceId = 0;
let lastAuthor = null;
let lastDateStr = null;
let emptyShown = false;

showEmpty();

scrollBtn.addEventListener("click", () => {
  window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
});

window.addEventListener("scroll", () => {
  scrollBtn.classList.toggle("visible", !isAtBottom());
});

async function poll() {
  try {
    const res = await fetch(`${API_URL}?since_id=${sinceId}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const messages = await res.json();
    setStatus(true);
    appendBatch(messages);
  } catch (err) {
    setStatus(false);
    console.error("poll error:", err);
  }
}

function setStatus(live) {
  statusEl.textContent = live ? "● live" : "● disconnected";
  statusEl.classList.toggle("disconnected", !live);
}

function isAtBottom() {
  const threshold = 100;
  return window.innerHeight + window.scrollY >= document.body.scrollHeight - threshold;
}

function formatTime(iso) {
  const d = new Date(iso);
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  if (sameDay) return `${hh}:${mm}`;
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return `${months[d.getMonth()]} ${d.getDate()} · ${hh}:${mm}`;
}

function formatDayHeader(iso) {
  const d = new Date(iso);
  const days = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];
  const months = ["January","February","March","April","May","June","July","August","September","October","November","December"];
  return `${days[d.getDay()]}, ${months[d.getMonth()]} ${d.getDate()}`;
}

function showEmpty() {
  messagesEl.innerHTML = '<div class="empty">no messages yet</div>';
  emptyShown = true;
  scrollBtn.classList.remove("visible");
}

function clearEmpty() {
  if (emptyShown) {
    messagesEl.innerHTML = "";
    emptyShown = false;
  }
}

function appendBatch(messages) {
  if (messages.length === 0) return;

  const wasAtBottom = isAtBottom();
  clearEmpty();

  for (const msg of messages) {
    const dateStr = new Date(msg.created_at).toDateString();

    if (dateStr !== lastDateStr) {
      const sep = document.createElement("div");
      sep.className = "day-separator";
      sep.textContent = formatDayHeader(msg.created_at);
      messagesEl.appendChild(sep);
      lastAuthor = null;
    }

    const isStreak = msg.author === lastAuthor;
    appendMessage(msg, isStreak);

    lastAuthor = msg.author;
    lastDateStr = dateStr;
    if (msg.id > sinceId) sinceId = msg.id;
  }

  if (wasAtBottom) {
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
  }
  scrollBtn.classList.toggle("visible", !isAtBottom());
}

function appendMessage(msg, isStreak) {
  const isSelf = selfName && msg.author === selfName;
  const wrapper = document.createElement("div");
  wrapper.className = `message ${isSelf ? "self" : "other"}`;
  if (isStreak) wrapper.classList.add("streak-continuation");

  if (!isStreak) {
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = `${msg.author} · ${formatTime(msg.created_at)}`;
    wrapper.appendChild(meta);
  }

  const content = document.createElement("div");
  content.className = "content";
  content.textContent = msg.content;
  wrapper.appendChild(content);

  messagesEl.appendChild(wrapper);
}

poll();
setInterval(poll, POLL_INTERVAL_MS);
