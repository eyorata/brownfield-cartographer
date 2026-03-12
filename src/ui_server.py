from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse


_ROOT = Path(__file__).resolve().parents[1]
_CARTO_DIR = (_ROOT / ".cartography").resolve()
_RUNS_DIR = (_CARTO_DIR / "ui_runs").resolve()


def _pick_python() -> str:
    """
    Prefer this repo's venv python if present; otherwise fall back to current interpreter.
    """
    venv_py = (_ROOT / ".venv" / "Scripts" / "python.exe").resolve()
    if venv_py.exists():
        return str(venv_py)
    return sys.executable


def _read_tail(path: Path, max_bytes: int = 64_000) -> str:
    if not path.exists():
        return ""
    data = path.read_bytes()
    if len(data) > max_bytes:
        data = data[-max_bytes:]
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _parse_trace(trace_path: Path) -> Dict[str, Any]:
    """
    Converts cartography_trace.jsonl into per-phase status.
    """
    phases: Dict[str, Dict[str, Any]] = {}
    if not trace_path.exists():
        return {"phases": phases, "events": 0}

    events = 0
    for line in trace_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        events += 1
        if ev.get("event") == "phase_start":
            ph = str(ev.get("phase") or "")
            phases.setdefault(ph, {})["started_at"] = ev.get("ts")
            phases.setdefault(ph, {})["status"] = "running"
        if ev.get("event") == "phase_end":
            ph = str(ev.get("phase") or "")
            phases.setdefault(ph, {})["ended_at"] = ev.get("ts")
            phases.setdefault(ph, {})["status"] = "done"

    return {"phases": phases, "events": events}


class _JobStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def create(self, requested_path: str) -> Dict[str, Any]:
        job_id = uuid.uuid4().hex[:12]
        out_dir = (_RUNS_DIR / job_id).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        log_path = out_dir / "ui.log"
        job = {
            "id": job_id,
            "requested_path": requested_path,
            "resolved_repo_path": None,
            "status": "queued",
            "created_at": time.time(),
            "started_at": None,
            "ended_at": None,
            "exit_code": None,
            "error": None,
            "output_dir": str(out_dir),
            "log_path": str(log_path),
        }
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            j = self._jobs.get(job_id)
            return dict(j) if j else None

    def update(self, job_id: str, **kwargs: Any) -> None:
        with self._lock:
            if job_id not in self._jobs:
                return
            self._jobs[job_id].update(kwargs)


JOBS = _JobStore()


def _run_analyze_job(job_id: str) -> None:
    job = JOBS.get(job_id)
    if not job:
        return

    out_dir = Path(job["output_dir"]).resolve()
    log_path = Path(job["log_path"]).resolve()

    py = _pick_python()
    cmd = [py, str((_ROOT / "src" / "cli.py").resolve()), "analyze", job["requested_path"], "--output-dir", str(out_dir)]

    JOBS.update(job_id, status="running", started_at=time.time())

    # Stream stdout/stderr to a log file so the UI can poll it.
    resolved_repo_path = None
    try:
        with log_path.open("w", encoding="utf-8") as lf:
            lf.write(" ".join(cmd) + "\n\n")
            lf.flush()

            proc = subprocess.Popen(
                cmd,
                cwd=str(_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            assert proc.stdout is not None
            for line in proc.stdout:
                lf.write(line)
                lf.flush()
                if line.startswith("Running analysis on:"):
                    # CLI prints the resolved path here (including after clone).
                    resolved_repo_path = line.split("Running analysis on:", 1)[1].strip()
                    JOBS.update(job_id, resolved_repo_path=resolved_repo_path)

            proc.wait()
            JOBS.update(job_id, exit_code=int(proc.returncode))
            if proc.returncode == 0:
                JOBS.update(job_id, status="done")
            else:
                JOBS.update(job_id, status="error", error=f"analyze exited with code {proc.returncode}")
    except Exception as e:
        JOBS.update(job_id, status="error", error=str(e))
    finally:
        JOBS.update(job_id, ended_at=time.time())


_INDEX_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Brownfield Cartographer</title>
    <style>
      :root {
        --bg0: #0b1020;
        --bg1: #0f1a2e;
        --card: rgba(255, 255, 255, 0.06);
        --card2: rgba(255, 255, 255, 0.10);
        --text: rgba(255, 255, 255, 0.92);
        --muted: rgba(255, 255, 255, 0.70);
        --accent: #f7c948;
        --good: #27ae60;
        --bad: #e74c3c;
        --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        --serif: "Palatino Linotype", Palatino, Georgia, "Times New Roman", serif;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        color: var(--text);
        font-family: var(--serif);
        background: radial-gradient(1200px 700px at 15% 10%, #1c2a55 0%, transparent 60%),
                    radial-gradient(900px 600px at 85% 20%, #3b2d4a 0%, transparent 55%),
                    linear-gradient(160deg, var(--bg0), var(--bg1));
        min-height: 100vh;
      }
      header {
        padding: 28px 18px 14px;
        max-width: 1100px;
        margin: 0 auto;
      }
      h1 {
        margin: 0;
        letter-spacing: 0.2px;
        font-weight: 700;
        font-size: 28px;
      }
      .sub {
        margin-top: 6px;
        color: var(--muted);
        font-family: system-ui, -apple-system, Segoe UI, Arial, sans-serif;
        font-size: 13px;
      }
      main {
        padding: 12px 18px 30px;
        max-width: 1100px;
        margin: 0 auto;
        display: grid;
        grid-template-columns: 1.2fr 1fr;
        gap: 14px;
      }
      @media (max-width: 920px) {
        main { grid-template-columns: 1fr; }
      }
      .card {
        background: var(--card);
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 14px;
        padding: 14px;
        backdrop-filter: blur(10px);
      }
      .card h2 {
        margin: 0 0 10px 0;
        font-size: 16px;
        font-family: system-ui, -apple-system, Segoe UI, Arial, sans-serif;
        letter-spacing: 0.2px;
      }
      label { display: block; font-size: 12px; color: var(--muted); margin: 10px 0 6px; font-family: system-ui, -apple-system, Segoe UI, Arial, sans-serif; }
      input[type=text] {
        width: 100%;
        padding: 10px 10px;
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.14);
        background: rgba(0,0,0,0.22);
        color: var(--text);
        font-family: var(--mono);
      }
      button {
        margin-top: 10px;
        padding: 10px 12px;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.18);
        background: linear-gradient(180deg, rgba(247,201,72,0.95), rgba(247,201,72,0.70));
        color: #171717;
        font-weight: 700;
        cursor: pointer;
        font-family: system-ui, -apple-system, Segoe UI, Arial, sans-serif;
      }
      button:disabled { opacity: 0.6; cursor: not-allowed; }
      .row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
      @media (max-width: 520px) { .row { grid-template-columns: 1fr; } }

      .pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 10px;
        border-radius: 999px;
        font-family: system-ui, -apple-system, Segoe UI, Arial, sans-serif;
        font-size: 12px;
        border: 1px solid rgba(255,255,255,0.14);
        background: rgba(0,0,0,0.20);
      }
      .dot { width: 8px; height: 8px; border-radius: 99px; background: rgba(255,255,255,0.50); }
      .dot.good { background: var(--good); }
      .dot.bad { background: var(--bad); }
      .dot.run { background: var(--accent); }

      pre {
        margin: 0;
        white-space: pre-wrap;
        word-break: break-word;
        padding: 12px;
        border-radius: 12px;
        background: rgba(0,0,0,0.30);
        border: 1px solid rgba(255,255,255,0.10);
        font-family: var(--mono);
        font-size: 12px;
        line-height: 1.35;
        max-height: 520px;
        overflow: auto;
      }
      .small { font-size: 12px; color: var(--muted); font-family: system-ui, -apple-system, Segoe UI, Arial, sans-serif; }
      a { color: var(--accent); text-decoration: none; }
      a:hover { text-decoration: underline; }
    </style>
  </head>
  <body>
    <header>
      <h1>Brownfield Cartographer</h1>
      <div class="sub">Run the four-phase pipeline (Surveyor, Hydrologist, Semanticist, Archivist) on a local repo path or GitHub URL, then inspect artifacts.</div>
    </header>
    <main>
      <section class="card">
        <h2>Analyze</h2>
        <label>Repo path or GitHub URL</label>
        <input id="repo" type="text" placeholder="e.g. .\\_targets\\dbt-core  OR  https://github.com/dbt-labs/dbt-core" />
        <button id="run">Run Analysis</button>
        <div style="margin-top:12px;">
          <div class="pill"><span id="s_dot" class="dot"></span><span id="s_text">idle</span></div>
          <span id="job_meta" class="small" style="margin-left:10px;"></span>
        </div>
        <div style="margin-top:12px;" class="row">
          <div class="pill"><span id="p_surveyor" class="dot"></span><span>Surveyor</span></div>
          <div class="pill"><span id="p_hydrologist" class="dot"></span><span>Hydrologist</span></div>
          <div class="pill"><span id="p_semanticist" class="dot"></span><span>Semanticist</span></div>
          <div class="pill"><span id="p_archivist" class="dot"></span><span>Archivist</span></div>
        </div>
        <div style="margin-top:12px;" class="small" id="paths"></div>
      </section>
      <section class="card">
        <h2>Logs</h2>
        <pre id="log">(no job yet)</pre>
      </section>
    </main>
    <script>
      const runBtn = document.getElementById('run');
      const repoInp = document.getElementById('repo');
      const logEl = document.getElementById('log');
      const sDot = document.getElementById('s_dot');
      const sText = document.getElementById('s_text');
      const jobMeta = document.getElementById('job_meta');
      const pathsEl = document.getElementById('paths');
      const phaseDots = {
        surveyor: document.getElementById('p_surveyor'),
        hydrologist: document.getElementById('p_hydrologist'),
        semanticist: document.getElementById('p_semanticist'),
        archivist: document.getElementById('p_archivist'),
      };

      let currentJob = null;
      let pollTimer = null;

      function setDot(dot, state) {
        dot.className = 'dot';
        if (state === 'done') dot.classList.add('good');
        else if (state === 'error') dot.classList.add('bad');
        else if (state === 'running') dot.classList.add('run');
      }

      function setStatus(status) {
        setDot(sDot, status === 'done' ? 'done' : (status === 'error' ? 'error' : (status === 'running' ? 'running' : 'idle')));
        sText.textContent = status;
      }

      async function start() {
        const path = repoInp.value.trim();
        if (!path) return;
        runBtn.disabled = true;
        pathsEl.textContent = '';
        Object.values(phaseDots).forEach(d => setDot(d, 'idle'));
        setStatus('starting');
        logEl.textContent = '';

        const resp = await fetch('/api/analyze', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({path}),
        });
        const data = await resp.json();
        currentJob = data.id;
        jobMeta.textContent = `job ${currentJob}`;
        setStatus('running');
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(poll, 1200);
      }

      async function poll() {
        if (!currentJob) return;
        const resp = await fetch('/api/job?id=' + encodeURIComponent(currentJob));
        const data = await resp.json();
        setStatus(data.status);
        logEl.textContent = data.log || '';
        if (data.phases) {
          for (const [ph, dot] of Object.entries(phaseDots)) {
            const st = (data.phases[ph] && data.phases[ph].status) ? data.phases[ph].status : 'idle';
            setDot(dot, st);
          }
        }
        if (data.resolved_repo_path || data.output_dir) {
          const bits = [];
          if (data.resolved_repo_path) bits.push(`target: <code>${data.resolved_repo_path}</code>`);
          if (data.output_dir) bits.push(`ui artifacts: <code>${data.output_dir}</code>`);
          pathsEl.innerHTML = bits.join('<br/>');
        }
        if (data.status === 'done' || data.status === 'error') {
          runBtn.disabled = false;
          if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
        }
      }

      runBtn.addEventListener('click', start);
    </script>
  </body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "CartographyUI/0.1"

    def _send_json(self, obj: Any, status: int = 200) -> None:
        data = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_text(self, text: str, status: int = 200, content_type: str = "text/plain; charset=utf-8") -> None:
        data = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_text(_INDEX_HTML, content_type="text/html; charset=utf-8")
            return

        if parsed.path == "/api/job":
            qs = parse_qs(parsed.query or "")
            job_id = (qs.get("id") or [""])[0]
            job = JOBS.get(job_id)
            if not job:
                self._send_json({"error": "job not found"}, status=404)
                return
            out_dir = Path(job["output_dir"]).resolve()
            log = _read_tail(Path(job["log_path"]), max_bytes=120_000)
            trace_info = _parse_trace(out_dir / "cartography_trace.jsonl")
            self._send_json(
                {
                    "id": job["id"],
                    "requested_path": job["requested_path"],
                    "resolved_repo_path": job.get("resolved_repo_path"),
                    "status": job["status"],
                    "exit_code": job.get("exit_code"),
                    "error": job.get("error"),
                    "output_dir": str(out_dir),
                    "log": log,
                    "phases": trace_info.get("phases"),
                    "trace_events": trace_info.get("events"),
                }
            )
            return

        self._send_json({"error": "not found"}, status=404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/analyze":
            self._send_json({"error": "not found"}, status=404)
            return

        try:
            length = int(self.headers.get("Content-Length") or "0")
        except Exception:
            length = 0
        body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            payload = {}

        requested_path = str(payload.get("path") or "").strip()
        if not requested_path:
            self._send_json({"error": "missing 'path'"}, status=400)
            return

        job = JOBS.create(requested_path=requested_path)
        t = threading.Thread(target=_run_analyze_job, args=(job["id"],), daemon=True)
        t.start()

        self._send_json({"id": job["id"], "status": job["status"], "output_dir": job["output_dir"]}, status=200)

    def log_message(self, format: str, *args: Any) -> None:
        # Keep console quiet; UI polling can be noisy.
        return


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    _CARTO_DIR.mkdir(parents=True, exist_ok=True)
    _RUNS_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, int(port)), Handler)
    print(f"UI server running on http://{host}:{port}")
    print(f"UI working dir: {_RUNS_DIR}")
    server.serve_forever()

