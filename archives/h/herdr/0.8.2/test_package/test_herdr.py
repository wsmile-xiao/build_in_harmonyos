#!/usr/bin/env python3
"""Test herdr: version check, server lifecycle, workspace API."""

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time


def pick_tmpdir():
    """Pick a tmp dir that can actually create Unix sockets.

    On HarmonyOS TMPDIR may point at the file_manager mount (hmdfs), which
    rejects bind() with EPERM (E337) — herdr server then exits code 1.
    """
    candidates = []
    for var in ("OHC_TEST_TMPDIR", "TMPDIR", "TMP", "TEMP"):
        if os.environ.get(var):
            candidates.append(os.environ[var])
    candidates += ["/data/storage/el2/base/cache", "/data/local/tmp", "/tmp"]
    for cand in candidates:
        if not cand or not os.path.isdir(cand):
            continue
        try:
            d = tempfile.mkdtemp(prefix="herdr-test-", dir=cand)
            probe = os.path.join(d, "probe.sock")
            sock = socket.socket(socket.AF_UNIX)
            sock.bind(probe)
            sock.close()
            os.unlink(probe)
            return d
        except OSError:
            shutil.rmtree(d, ignore_errors=True)
            continue
    return tempfile.mkdtemp(prefix="herdr-test-")


def main():
    if len(sys.argv) != 2:
        print("usage: test_herdr.py <herdr-binary>", file=sys.stderr)
        return 2
    binary = sys.argv[1]
    tmpdir = pick_tmpdir()
    print(f"[info] tmpdir: {tmpdir} (TMPDIR={os.environ.get('TMPDIR') or '<unset>'})", flush=True)
    try:
        env = dict(os.environ)
        # Ensure bash is in PATH and SHELL is set (herdr workspace create needs a shell)
        bash = shutil.which("bash") or "/data/app/bin/bash"
        bash_dir = os.path.dirname(bash)
        if bash_dir not in env.get("PATH", ""):
            env["PATH"] = bash_dir + ":" + env.get("PATH", "")
        env["SHELL"] = bash
        env.update({
            "HOME": tmpdir,
            "XDG_CONFIG_HOME": os.path.join(tmpdir, "config"),
            "XDG_STATE_HOME": os.path.join(tmpdir, "state"),
            "HERDR_CONFIG_PATH": os.path.join(tmpdir, "config.toml"),
            "HERDR_SOCKET_PATH": os.path.join(tmpdir, "herdr.sock"),
        })

        # 1. version check
        result = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, f"herdr --version failed: {result.stderr}"
        assert "0.8.2" in result.stdout, f"expected 0.8.2 in version, got {result.stdout}"
        print(f"[pass] version: {result.stdout.strip()}")

        # 2. server start
        server = subprocess.Popen(
            [binary, "server"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
        )
        time.sleep(3)
        try:
            ret = server.poll()
            if ret is not None:
                out, err = server.communicate(timeout=5)
                print(f"[FAIL] herdr server exited early: code {ret}", flush=True)
                print(f"[FAIL] server stdout: {out.decode(errors='replace')}", flush=True)
                print(f"[FAIL] server stderr: {err.decode(errors='replace')}", flush=True)
                for log in (
                    os.path.join(tmpdir, "config", "herdr", "herdr-server.log"),
                    os.path.join(env["HERDR_CONFIG_PATH"], "herdr-server.log"),
                ):
                    if os.path.isfile(log):
                        print(f"[FAIL] server log {log}:", flush=True)
                        print(open(log, encoding="utf-8", errors="replace").read()[-2000:], flush=True)
            assert ret is None, f"herdr server exited early: code {ret}"

            # 3. status check
            result = subprocess.run(
                [binary, "status", "server"], capture_output=True, text=True,
                timeout=10, env=env,
            )
            assert result.returncode == 0
            assert "running" in result.stdout
            assert "0.8.2" in result.stdout
            print("[pass] server status: running")

            # 4. workspace create
            result = subprocess.run(
                [binary, "workspace", "create", "--label", "conan-test", "--no-focus"],
                capture_output=True, text=True, timeout=15, env=env,
            )
            if result.returncode != 0:
                print(f"[FAIL] workspace create stdout: {result.stdout}", flush=True)
                print(f"[FAIL] workspace create stderr: {result.stderr}", flush=True)
            assert result.returncode == 0, f"workspace create failed: {result.stderr}"
            output = json.loads(result.stdout)
            assert output["result"]["type"] == "workspace_created"
            ws_id = output["result"]["workspace"]["workspace_id"]
            print(f"[pass] workspace created: {ws_id}")

            # 5. workspace list
            result = subprocess.run(
                [binary, "workspace", "list"],
                capture_output=True, text=True, timeout=10, env=env,
            )
            assert result.returncode == 0
            ws_list = json.loads(result.stdout)
            ws_ids = [w["workspace_id"] for w in ws_list["result"]["workspaces"]]
            assert ws_id in ws_ids, f"workspace {ws_id} not in list"
            print(f"[pass] workspace list contains {ws_id}")
        finally:
            server.terminate()
            server.wait(timeout=5)

        print("herdr version/server/workspace checks passed")
        return 0
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())