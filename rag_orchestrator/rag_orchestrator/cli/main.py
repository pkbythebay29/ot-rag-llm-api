from __future__ import annotations

import os
import sys
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
import psutil  # runtime discovery (by port), uptime, stop

app = typer.Typer(help="Krionis Orchestrator CLI")

# Defaults (env overridable)
DEFAULT_HOST = os.getenv("ORCH_HOST", "0.0.0.0")
DEFAULT_PORT = int(os.getenv("ORCH_PORT", "8080"))
DEFAULT_LOG = os.getenv("ORCH_LOG", "orchestrator.log")

UVICORN_APP = "rag_orchestrator.api.app:app"

# ---------------------------
# helpers
# ---------------------------

def _spawn_detached(cmd: list[str], log_path: Optional[str]) -> subprocess.Popen:
    """
    Spawn uvicorn detached from the current console, cross-platform.
    Stdout/stderr optionally redirected to a log file.
    """
    stdout = stderr = subprocess.DEVNULL
    if log_path:
        # ensure parent dir exists, open in line-buffered text mode
        p = Path(log_path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        logf = open(p, "a", buffering=1, encoding="utf-8")
        stdout = stderr = logf  # let Popen keep the handle

    if sys.platform == "win32":
        DETACHED = 0x00000008         # DETACHED_PROCESS
        NEW_GROUP = 0x00000200        # CREATE_NEW_PROCESS_GROUP
        return subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            creationflags=DETACHED | NEW_GROUP,
            close_fds=False,
        )
    else:
        # Start new session so ^C in this shell doesn't kill the child
        return subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            preexec_fn=os.setsid,  # new process group
            close_fds=True,
        )


def _find_server_proc(port: int) -> Optional[psutil.Process]:
    """
    Return the process that is LISTENing on `port` and looks like uvicorn.
    If multiple procs match, prefer the oldest (master) process.
    """
    cand: list[psutil.Process] = []
    for p in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            for c in p.connections(kind="inet"):
                if (
                    c.status == psutil.CONN_LISTEN
                    and c.laddr
                    and c.laddr.port == port
                ):
                    # sanity: looks like uvicorn running our app
                    cmd = " ".join(p.info.get("cmdline") or [])
                    if "uvicorn" in (p.info.get("name") or "").lower() or "uvicorn" in cmd.lower():
                        cand.append(p)
                        break
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue

    if not cand:
        return None

    # choose the oldest (master) process
    cand.sort(key=lambda x: x.info.get("create_time", float("inf")))
    return cand[0]


def _fmt_uptime(create_time: float) -> str:
    dt = datetime.fromtimestamp(create_time, tz=timezone.utc)
    delta = datetime.now(tz=timezone.utc) - dt
    total = int(delta.total_seconds())
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _terminate_proc(p: psutil.Process, timeout: float = 10.0) -> bool:
    """
    Try graceful termination of the *group*; fall back to kill.
    """
    try:
        if sys.platform == "win32":
            # terminate whole tree
            subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
            return True
        else:
            # send SIGTERM to the process group
            try:
                os.killpg(p.pid, signal.SIGTERM)  # type: ignore[arg-type]
            except Exception:
                p.terminate()
            try:
                psutil.wait_procs([p], timeout=timeout)
                return True
            except psutil.TimeoutExpired:
                try:
                    os.killpg(p.pid, signal.SIGKILL)  # type: ignore[arg-type]
                except Exception:
                    p.kill()
                return True
    except psutil.NoSuchProcess:
        return True
    except Exception:
        return False


# ---------------------------
# Commands
# ---------------------------

@app.command()
def start(
    host: str = typer.Option(DEFAULT_HOST, help="Host to bind"),
    port: int = typer.Option(DEFAULT_PORT, help="Port to bind"),
    log_file: str = typer.Option(DEFAULT_LOG, help="Optional log file (stdout/stderr)."),
    workers: int = typer.Option(1, help="Number of uvicorn workers"),
):
    """
    Start the orchestrator as a detached background process.
    No PID file is used; discovery is by port.
    """
    # if something already listens on the port, don't start another
    existing = _find_server_proc(port)
    if existing:
        up = _fmt_uptime(existing.create_time())
        typer.echo(f"Already running (pid {existing.pid}, uptime {up}).")
        raise typer.Exit(0)

    cmd = [
        sys.executable, "-m", "uvicorn",
        UVICORN_APP,
        "--host", host,
        "--port", str(port),
        "--workers", str(workers),
        "--log-level", "info",
    ]

    proc = _spawn_detached(cmd, log_file or None)

    # wait until the *real* uvicorn server is listening
    target: Optional[psutil.Process] = None
    for _ in range(60):  # ~60 seconds
        time.sleep(1)
        target = _find_server_proc(port)
        if target:
            break

    if not target:
        typer.echo("Failed to start (server did not begin listening).", err=True)
        # last resort: try to kill the launcher
        try:
            psutil.Process(proc.pid).kill()
        except Exception:
            pass
        raise typer.Exit(1)

    up = _fmt_uptime(target.create_time())
    where = f"http://{host}:{port}"
    if log_file:
        typer.echo(f"Started orchestrator (pid {target.pid}, uptime {up}). Logs -> {Path(log_file).resolve()}")
    else:
        typer.echo(f"Started orchestrator (pid {target.pid}, uptime {up}).")
    typer.echo(f"Uvicorn listening on {where}")


@app.command()
def stop(
    port: int = typer.Option(DEFAULT_PORT, help="Port the orchestrator is using"),
):
    """
    Stop the orchestrator by discovering the server on `--port`.
    """
    p = _find_server_proc(port)
    if not p:
        typer.echo("Not running.")
        raise typer.Exit(0)

    ok = _terminate_proc(p)
    if ok:
        typer.echo("Stopped.")
    else:
        typer.echo("Failed to stop.", err=True)
        raise typer.Exit(1)


@app.command()
def restart(
    host: str = typer.Option(DEFAULT_HOST),
    port: int = typer.Option(DEFAULT_PORT),
    log_file: str = typer.Option(DEFAULT_LOG),
    workers: int = typer.Option(1),
):
    """
    Restart the orchestrator (no PID files).
    """
    stop.callback(port=port)  # type: ignore[attr-defined]
    time.sleep(0.5)
    start.callback(host=host, port=port, log_file=log_file, workers=workers)  # type: ignore[attr-defined]


@app.command()
def status(
    port: int = typer.Option(DEFAULT_PORT, help="Port to probe for the orchestrator"),
):
    """
    Show run status (pid and uptime) by probing the listening port.
    """
    p = _find_server_proc(port)
    if not p:
        typer.echo("Not running.")
        raise typer.Exit(0)

    up = _fmt_uptime(p.create_time())
    typer.echo(f"Running (pid {p.pid}, uptime {up}).")


@app.command()
def dev(
    host: str = typer.Option(DEFAULT_HOST, help="Host to bind"),
    port: int = typer.Option(DEFAULT_PORT, help="Port to bind"),
):
    """
    Run in foreground with auto-reload (developer mode).
    """
    os.execv(sys.executable, [
        sys.executable, "-m", "uvicorn",
        UVICORN_APP,
        "--host", host, "--port", str(port),
        "--reload",
    ])


def main() -> None:
    app()
