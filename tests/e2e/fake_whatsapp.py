"""
Imitation of WhatsApp Web's structure for testing the browser automation end to end.
Mirrors the selectors the app relies on; it cannot prove the real site still matches them.
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8599
LOG = []

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>WhatsApp</title></head><body>
<div id="pane-side">Chats</div>
<div id="main"><div id="messages"></div><footer id="footer" hidden>
  <button title="Attach" id="attach">+</button>
  <input type="file" id="file" style="display:none">
  <div contenteditable="true" id="box" style="border:1px solid #999;min-height:20px"></div>
</footer></div>
<script>
const params = new URLSearchParams(location.search);
const phone = params.get("phone");
const log = (entry) => fetch("/log", {method: "POST", body: JSON.stringify({phone, ...entry})});
function addPending() {
  const s = document.createElement("span");
  s.dataset.icon = "msg-time";
  document.getElementById("messages").appendChild(s);
  setTimeout(() => (s.dataset.icon = "msg-check"), 800);
}
if (location.pathname === "/send") {
  setTimeout(() => {
    if (phone === "910000000000") {
      document.body.insertAdjacentHTML("beforeend", "<div role='dialog'>Phone number shared via url is invalid.</div>");
      return;
    }
    document.getElementById("footer").hidden = false;
    setTimeout(() => (document.getElementById("box").innerText = params.get("text") || ""), 400);
  }, 600);
}
document.getElementById("box").addEventListener("keydown", (e) => {
  if (e.key !== "Enter") return;
  e.preventDefault();
  const box = e.target;
  log({kind: "text", text: box.innerText});
  box.innerText = "";
  addPending();
});
document.getElementById("attach").addEventListener("click", () => {});
document.getElementById("file").addEventListener("change", (e) => {
  const f = e.target.files[0];
  const dlg = document.createElement("div");
  dlg.setAttribute("role", "dialog");
  dlg.innerHTML = "<span data-icon='send' style='display:inline-block;width:30px;height:30px;background:green'></span>";
  dlg.querySelector("span").onclick = () => { log({kind: "file", name: f.name, size: f.size}); dlg.remove(); addPending(); };
  document.body.appendChild(dlg);
});
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, body: bytes, ctype: str):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/log"):
            self._send(json.dumps(LOG).encode(), "application/json")
        else:
            self._send(PAGE.encode(), "text/html; charset=utf-8")

    def do_POST(self):
        LOG.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
        self._send(b"{}", "application/json")


if __name__ == "__main__":
    print("fake WhatsApp ready", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
