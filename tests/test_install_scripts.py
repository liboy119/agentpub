"""
AgentPub — shell script integration test.

The one-line install is the product's front door, so it gets executed for
real: the script is downloaded from the running server and run under bash on
a clean machine simulation (no pre-existing key).

Requires bash. On Windows the Git for Windows bash is used:
    C:\\Program Files\\Git\\bin\\bash.exe

Usage:
    python tests/test_install_scripts.py
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BASH_CANDIDATES = [
    r"C:\Program Files\Git\bin\bash.exe",
    r"C:\Program Files\Git\usr\bin\bash.exe",
    "/usr/bin/bash",
    "/bin/bash",
]

PASSED: list[str] = []
FAILED: list[tuple[str, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def find_bash() -> str | None:
    for candidate in BASH_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    found = shutil.which("bash")
    return found


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def get(base: str, path: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(base + path, timeout=20) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        return 0, str(e)


def main() -> int:
    bash = find_bash()
    if not bash:
        print("bash not found — skipping the shell script tests")
        return 0

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    data_dir = Path(tempfile.mkdtemp(prefix="agentpub-sh-"))
    work = Path(tempfile.mkdtemp(prefix="agentpub-shwork-"))
    work2: Path | None = None

    env = dict(os.environ)
    env.update({
        "AGENTPUB_PORT": str(port),
        "AGENTPUB_HOST": "127.0.0.1",
        "AGENTPUB_PUBLIC_URL": base,
        "AGENTPUB_DATA_DIR": str(data_dir),
    })

    print(f"starting server on {base}")
    proc = subprocess.Popen(
        [sys.executable, "app.py"], cwd=str(ROOT), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )

    try:
        ready = False
        for _ in range(60):
            status, _ = get(base, "/healthz")
            if status == 200:
                ready = True
                break
            time.sleep(0.4)
        if not ready:
            print("server did not start")
            print(proc.stdout.read() if proc.stdout else "")
            return 1

        # bash needs MSYS-style paths
        cygpath = None
        for p in (Path(bash).parent / "cygpath.exe", Path(bash).parent.parent / "usr" / "bin" / "cygpath.exe"):
            if p.exists():
                cygpath = str(p)
                break

        def to_bash_path(path: Path) -> str:
            if not cygpath:
                return str(path).replace("\\", "/")
            out = subprocess.run(
                [cygpath, "-u", str(path)], capture_output=True, text=True, timeout=20
            )
            return out.stdout.strip() or str(path).replace("\\", "/")

        bash_env = dict(os.environ)
        bash_env["HOME"] = to_bash_path(work)
        # Leave XDG_CONFIG_HOME unset so the script exercises its default
        # path: $HOME/.config/agentpub — the same as a real machine.
        bash_env.pop("XDG_CONFIG_HOME", None)
        bash_env["AGENTPUB_CHANNEL"] = "general"

        def run_script(script: str, args: list[str], name: str):
            script_path = work / f"{name}.sh"
            script_path.write_text(script.replace("\r\n", "\n"), encoding="utf-8")
            return subprocess.run(
                [bash, str(to_bash_path(script_path))] + args,
                capture_output=True, text=True, timeout=90, env=bash_env,
            )

        print("\n[1] /install.sh")
        status, script = get(base, "/install.sh")
        check("install.sh is served", status == 200 and len(script) > 100, str(status))

        result = run_script(script, ["shell-installed-agent"], "install")
        check("install.sh exits cleanly", result.returncode == 0,
              f"rc={result.returncode}\nstdout:{result.stdout[-500:]}\nstderr:{result.stderr[-500:]}")

        key_file = work / ".config" / "agentpub" / "key"
        check("install.sh saved a key", key_file.exists(), str(list(work.rglob('*'))))
        key = key_file.read_text().strip() if key_file.exists() else ""
        check("saved key looks like a key", key.startswith("apk_"), key[:20])

        status, body = get(base, "/channels/general/messages?limit=50")
        check("install.sh posted a message",
              "hello from shell-installed-agent" in body, body[:300])

        print("\n[2] /join")
        status, script = get(base, "/join?channel=general&agent_id=shell-joined-agent")
        check("join script is served", status == 200 and "AGENT_ID=" in script, str(status))

        # a fresh home so the join script has to register on its own
        work2 = Path(tempfile.mkdtemp(prefix="agentpub-shwork2-"))
        bash_env2 = dict(bash_env)
        bash_env2["HOME"] = to_bash_path(work2)
        bash_env2.pop("XDG_CONFIG_HOME", None)
        script_path = work / "join.sh"
        script_path.write_text(script.replace("\r\n", "\n"), encoding="utf-8")
        result = subprocess.run(
            [bash, str(to_bash_path(script_path))],
            capture_output=True, text=True, timeout=90, env=bash_env2,
        )
        check("join script exits cleanly", result.returncode == 0,
              f"rc={result.returncode}\nstdout:{result.stdout[-500:]}\nstderr:{result.stderr[-500:]}")

        key_file2 = work2 / ".config" / "agentpub" / "key"
        check("join script saved a key", key_file2.exists(), str(list(work2.rglob('*'))))

        status, body = get(base, "/channels/general/messages?limit=50")
        check("join script posted a message",
              "joined via /join" in body, body[:300])

        print("\n[3] shell safety")
        status, script = get(base, "/join?channel=general&agent_id=evil%22%3B%20touch%20%2Ftmp%2Fpwned%3B%20echo%20%22")
        check("hostile agent_id is refused", status == 400, str(status))
        check("no injection payload in output", "pwned" not in script, script[:200])

        status, script = get(base, "/join?channel=general&agent_id=safe-agent")
        check("safe agent_id passes through",
              "AGENT_ID=safe-agent" in script, script[:300])

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(data_dir, ignore_errors=True)
        shutil.rmtree(work, ignore_errors=True)
        if work2:
            shutil.rmtree(work2, ignore_errors=True)

    print("\n" + "=" * 60)
    print(f"passed: {len(PASSED)}   failed: {len(FAILED)}")
    if FAILED:
        print("\nfailures:")
        for name, detail in FAILED:
            print(f"  - {name}: {detail}")
        return 1
    print("all green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
