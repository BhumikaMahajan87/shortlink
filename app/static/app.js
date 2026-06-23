const $ = (id) => document.getElementById(id);
let currentCode = null;

$("shortenBtn").addEventListener("click", shorten);
$("url").addEventListener("keydown", (e) => {
  if (e.key === "Enter") shorten();
});
$("copyBtn").addEventListener("click", () => {
  navigator.clipboard.writeText($("shortLink").textContent);
  $("copyBtn").textContent = "Copied!";
  setTimeout(() => ($("copyBtn").textContent = "Copy"), 1200);
});
$("refreshBtn").addEventListener("click", () => currentCode && loadStats(currentCode));

async function shorten() {
  const url = $("url").value.trim();
  $("error").textContent = "";
  if (!url) return;
  const btn = $("shortenBtn");
  btn.disabled = true;
  try {
    const res = await fetch("/api/shorten", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Request failed");
    currentCode = data.code;
    $("result").style.display = "block";
    const link = $("shortLink");
    link.textContent = data.short_url;
    link.href = data.short_url;
    $("createdNote").textContent = data.created ? "(new)" : "(existing link reused)";
    loadStats(data.code);
  } catch (e) {
    $("error").textContent = "Error: " + e.message;
  } finally {
    btn.disabled = false;
  }
}

async function loadStats(code) {
  try {
    const res = await fetch(`/api/stats/${code}`);
    const data = await res.json();
    if (!res.ok) return;
    $("statsCard").style.display = "block";
    $("clickCount").textContent = data.clicks;
    $("longUrl").textContent = "-> " + data.long_url;
    const tbody = $("clicksTable").querySelector("tbody");
    tbody.innerHTML = data.recent_clicks
      .map(
        (c) =>
          `<tr><td>${c.timestamp.replace("T", " ").slice(0, 19)}</td>
           <td>${c.referer || "-"}</td><td>${(c.user_agent || "-").slice(0, 40)}</td></tr>`
      )
      .join("");
  } catch (_) {}
}
