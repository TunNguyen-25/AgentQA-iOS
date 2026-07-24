// studio/static/app.js — vanilla, no build. Renders the three M1 panels.
async function fetchJSON(path, opts) {
  const r = await fetch(path, opts);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) {
    throw new Error(body && body.error ? body.error : `HTTP ${r.status}`);
  }
  return body;
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function el(html) {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}

async function loadConfig() {
  const box = document.getElementById("config");
  try {
    const c = await fetchJSON("/api/config");
    box.textContent =
      `${c.platform} · ${c.app_id} · build:${c.build_policy} · appium:${c.appium_port}`;
  } catch (err) {
    box.textContent = `config error: ${err.message}`;
  }
}

async function loadRig() {
  const box = document.getElementById("rig");
  try {
    const r = await fetchJSON("/api/rig");
    box.innerHTML = "";
    const labels = { simulator: "Simulator", app_installed: "App", appium: "Appium", codegraph: "CodeGraph" };
    for (const key of Object.keys(labels)) {
      const ok = r[key];
      box.appendChild(el(`<span class="dot ${ok ? "ok" : "bad"}">${ok ? "●" : "○"} ${labels[key]}</span>`));
    }
  } catch (err) {
    box.textContent = `rig error: ${err.message}`;
  }
}

function setRunButtonsDisabled(disabled) {
  document.querySelectorAll("#tests button").forEach((b) => { b.disabled = disabled; });
}

async function loadTests() {
  const box = document.getElementById("tests");
  try {
    const data = await fetchJSON("/api/tests");
    box.innerHTML = "";
    box.appendChild(el(`<button id="run-all">Run all</button>`));
    document.getElementById("run-all").onclick = () => runTests("all");
    for (const t of data.tests) {
      const row = el(`<div class="test-row"><span>${esc(t)}</span></div>`);
      const btn = el(`<button>Run</button>`);
      btn.onclick = () => runTests(t);
      row.appendChild(btn);
      box.appendChild(row);
    }
    if (data.artifacts.length) {
      box.appendChild(el(`<div class="muted">Last failures: ${data.artifacts.map((a) => esc(a.name)).join(", ")}</div>`));
    }
  } catch (err) {
    box.textContent = `tests error: ${err.message}`;
  }
}

let activeRun = null;

async function runTests(target) {
  if (activeRun) { activeRun.close(); activeRun = null; }
  const out = document.getElementById("run-output");
  out.textContent = `$ pytest ${target}\n`;
  setRunButtonsDisabled(true);
  let run_id;
  try {
    ({ run_id } = await fetchJSON("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target, env: {} }),
    }));
  } catch (err) {
    out.textContent += `\n[error: ${err.message}]\n`;
    setRunButtonsDisabled(false);
    return;
  }
  const es = new EventSource(`/api/run/stream?id=${encodeURIComponent(run_id)}`);
  activeRun = es;
  es.onmessage = (e) => {
    if (e.data.startsWith("__END__:")) {
      out.textContent += `\n[exit ${e.data.split(":")[1]}]\n`;
      es.close();
      activeRun = null;
      loadTests();
      return;
    }
    out.textContent += e.data + "\n";
    out.scrollTop = out.scrollHeight;
  };
  es.onerror = () => {
    es.close();
    activeRun = null;
    setRunButtonsDisabled(false);
  };
}

async function loadMemory() {
  const box = document.getElementById("memory");
  try {
    const m = await fetchJSON("/api/memory");
    box.innerHTML = "";
    for (const kind of ["flows", "screens", "failures"]) {
      const group = el(`<div class="mem-group"><strong>${kind}</strong></div>`);
      for (const name of m[kind]) {
        const a = el(`<a href="#">${esc(name)}</a>`);
        a.onclick = async (ev) => {
          ev.preventDefault();
          try {
            const note = await fetchJSON(
              `/api/memory/note?path=${encodeURIComponent(kind + "/" + name + ".md")}`);
            document.getElementById("note-view").textContent = note.content;
          } catch (err) {
            document.getElementById("note-view").textContent = `note error: ${err.message}`;
          }
        };
        group.appendChild(a);
      }
      box.appendChild(group);
    }
  } catch (err) {
    box.textContent = `memory error: ${err.message}`;
  }
}

document.querySelectorAll("[data-refresh]").forEach((b) => {
  b.onclick = () => ({ rig: loadRig, memory: loadMemory }[b.dataset.refresh]());
});

loadConfig();
loadRig();
loadTests();
loadMemory();
