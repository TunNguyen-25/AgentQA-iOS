// studio/static/app.js — vanilla, no build. Renders the three M1 panels.
async function fetchJSON(path, opts) {
  const r = await fetch(path, opts);
  return r.json();
}

function el(html) {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}

async function loadConfig() {
  const c = await fetchJSON("/api/config");
  document.getElementById("config").textContent =
    `${c.platform} · ${c.app_id} · build:${c.build_policy} · appium:${c.appium_port}`;
}

async function loadRig() {
  const r = await fetchJSON("/api/rig");
  const box = document.getElementById("rig");
  box.innerHTML = "";
  const labels = { simulator: "Simulator", app_installed: "App", appium: "Appium", codegraph: "CodeGraph" };
  for (const key of Object.keys(labels)) {
    const ok = r[key];
    box.appendChild(el(`<span class="dot ${ok ? "ok" : "bad"}">${ok ? "●" : "○"} ${labels[key]}</span>`));
  }
}

async function loadTests() {
  const data = await fetchJSON("/api/tests");
  const box = document.getElementById("tests");
  box.innerHTML = "";
  box.appendChild(el(`<button id="run-all">Run all</button>`));
  document.getElementById("run-all").onclick = () => runTests("all");
  for (const t of data.tests) {
    const row = el(`<div class="test-row"><span>${t}</span></div>`);
    const btn = el(`<button>Run</button>`);
    btn.onclick = () => runTests(t);
    row.appendChild(btn);
    box.appendChild(row);
  }
  if (data.artifacts.length) {
    box.appendChild(el(`<div class="muted">Last failures: ${data.artifacts.map(a => a.name).join(", ")}</div>`));
  }
}

async function runTests(target) {
  const out = document.getElementById("run-output");
  out.textContent = `$ pytest ${target}\n`;
  const { run_id } = await fetchJSON("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target, env: {} }),
  });
  const es = new EventSource(`/api/run/stream?id=${run_id}`);
  es.onmessage = (e) => {
    if (e.data.startsWith("__END__:")) {
      out.textContent += `\n[exit ${e.data.split(":")[1]}]\n`;
      es.close();
      loadTests();
      return;
    }
    out.textContent += e.data + "\n";
    out.scrollTop = out.scrollHeight;
  };
}

async function loadMemory() {
  const m = await fetchJSON("/api/memory");
  const box = document.getElementById("memory");
  box.innerHTML = "";
  for (const kind of ["flows", "screens", "failures"]) {
    const group = el(`<div class="mem-group"><strong>${kind}</strong></div>`);
    for (const name of m[kind]) {
      const a = el(`<a href="#">${name}</a>`);
      a.onclick = async (ev) => {
        ev.preventDefault();
        const note = await fetchJSON(`/api/memory/note?path=${kind}/${name}.md`);
        document.getElementById("note-view").textContent = note.content;
      };
      group.appendChild(a);
    }
    box.appendChild(group);
  }
}

document.querySelectorAll("[data-refresh]").forEach((b) => {
  b.onclick = () => ({ rig: loadRig, memory: loadMemory }[b.dataset.refresh]());
});

loadConfig();
loadRig();
loadTests();
loadMemory();
