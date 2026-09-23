"""Exercise the packaged cntlm binary without external network."""

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path


def _writable_tmpbase():
    # OHOS /tmp is read-only (erofs); honor HMBS-injected writable dirs.
    for key in ("TMPDIR", "TMP", "TEMP"):
        val = os.environ.get(key)
        if val and val != "/tmp" and os.path.isdir(val) and os.access(val, os.W_OK):
            return val
    cwd = os.getcwd()
    if os.access(cwd, os.W_OK):
        return cwd
    return None


def _run_help(executable):
    proc = subprocess.run(
        [executable, "-h"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
        check=False,
    )
    combined = (proc.stdout + proc.stderr).decode(errors="replace")
    if proc.returncode != 0:
        raise AssertionError(f"cntlm -h exited {proc.returncode}: {combined[-500:]}")
    if "cntlm" not in combined.lower():
        raise AssertionError(f"help output missing cntlm marker: {combined[-500:]!r}")
    if "NTLM" not in combined:
        raise AssertionError("help output missing NTLM description")
    print("help output exposes CNTLM banner and usage")


def _run_version_banner(executable):
    proc = subprocess.run(
        [executable, "-h"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
        check=False,
    )
    combined = (proc.stdout + proc.stderr).decode(errors="replace")
    if "Accelerating NTLM" not in combined:
        raise AssertionError("version banner missing Accelerating NTLM marker")
    if "Usage:" not in combined:
        raise AssertionError("usage line missing from help output")
    print("version banner and usage line verified")


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _run_config_startup(executable):
    port = _free_port()
    # cntlm refuses to start without at least one parent Proxy
    # (main.c: croak("Parent proxy address missing")). The dummy parent
    # is never contacted: NoProxy * forces direct handling and the test
    # only opens a TCP connection to the Listen port.
    config = (
        "Username testuser\n"
        "Domain testdomain\n"
        "Password password\n"
        "Proxy 127.0.0.1:8080\n"
        "NoProxy *\n"
        f"Listen 127.0.0.1:{port}\n"
    )
    tmpbase = _writable_tmpbase()
    tmp_kwargs = {"dir": tmpbase} if tmpbase else {}
    with tempfile.TemporaryDirectory(**tmp_kwargs) as tmp:
        conf = Path(tmp) / "cntlm-test.conf"
        conf.write_text(config, encoding="utf-8")
        proc = subprocess.Popen(
            [executable, "-f", "-c", str(conf)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        try:
            connected = False
            last_error = None
            for _ in range(50):
                if proc.poll() is not None:
                    out = (proc.stdout.read() or b"").decode(errors="replace")
                    raise AssertionError(
                        f"cntlm exited early rc={proc.returncode}: {out[-800:]}"
                    )
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                        connected = True
                        break
                except OSError as exc:
                    last_error = exc
                    try:
                        proc.wait(timeout=0.2)
                    except subprocess.TimeoutExpired:
                        pass
            if not connected:
                raise AssertionError(f"cntlm did not listen on 127.0.0.1:{port}: {last_error}")
            print(f"cntlm accepted loopback connection on 127.0.0.1:{port}")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def main():
    executable = shutil.which("cntlm")
    if executable is None:
        raise AssertionError("packaged cntlm executable is not on PATH")
    print(f"using cntlm: {executable}")

    tests = [
        ("help output", lambda: _run_help(executable)),
        ("version banner", lambda: _run_version_banner(executable)),
        ("config startup", lambda: _run_config_startup(executable)),
    ]
    discovered = len(tests)
    passed = 0
    for name, fn in tests:
        fn()
        passed += 1
        print(f"PASS: {name}")

    print(f"cntlm test_package: {passed}/{discovered} passed")
    print(
        "HMBS_TEST_PACKAGE_RESULT="
        + json.dumps(
            {
                "executed": True,
                "passed": passed == discovered,
                "command": "python3 test_cntlm.py",
                "discovered": discovered,
                "passedCount": passed,
            }
        )
    )
    print(
        "HMBS_UPSTREAM_TEST_RESULT="
        + json.dumps(
            {
                "status": "no_tests",
                "framework": "none",
                "command": "none",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "upstream ships no test suite (no check/test target, no tests directory)",
            },
            ensure_ascii=False,
        )
    )
    if passed != discovered:
        sys.exit(1)


if __name__ == "__main__":
    main()
