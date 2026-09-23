#!/usr/bin/env python3
"""Functional test for the detachtty package binaries.

Usage: test_detachtty.py <detachtty-bin> <attachtty-bin> <tmpdir>

Three cases, each printing PASS/FAIL plus a final RESULT line:

  1. `detachtty --version` exits 0 and prints "detachtty version 11.0.0".
  2. `attachtty` with no arguments exits non-zero with a usage message.
  3. End-to-end socket test: spawn
     `detachtty --no-detach <tmpdir>/dt-<pid>.sock <sleep> 30`,
     poll for the socket file, run
     `attachtty <socket> hello-detachtty 1`, require exit 0, then
     terminate the server and remove the socket.

Exit code 0 means all cases passed.
"""

import hashlib
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time

PASS = 0
FAIL = 0


def ok(message):
    global PASS
    PASS += 1
    print("PASS: %s" % message)


def bad(message):
    global FAIL
    FAIL += 1
    print("FAIL: %s" % message)


def run(args, timeout=30):
    try:
        proc = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or b"") + (exc.stderr or b"")
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        return None, out
    except OSError as exc:
        return None, str(exc)


def main():
    if len(sys.argv) != 4:
        print("usage: test_detachtty.py <detachtty> <attachtty> <tmpdir>")
        return 2
    detachtty = sys.argv[1]
    attachtty = sys.argv[2]
    tmpdir = sys.argv[3]
    if not os.path.isfile(detachtty):
        print("FAIL: detachtty not found: %s" % detachtty)
        return 1
    if not os.path.isfile(attachtty):
        print("FAIL: attachtty not found: %s" % attachtty)
        return 1
    if not os.path.isdir(tmpdir):
        print("FAIL: tmpdir not found: %s" % tmpdir)
        return 1

    print("[test] detachtty binary: %s" % detachtty)
    print("[test] attachtty binary: %s" % attachtty)

    # Case 1: detachtty --version carries the real version string.
    rc, out = run([detachtty, "--version"])
    if rc == 0 and "detachtty version 11.0.0" in out:
        ok("detachtty --version prints 11.0.0 (%s)" % out.strip().splitlines()[0])
    else:
        bad("detachtty --version rc=%s out=%r" % (rc, out[:500]))

    # Case 2: attachtty with no arguments rejects with usage, non-zero.
    rc, out = run([attachtty])
    if rc not in (None, 0) and "usage:" in out:
        ok("attachtty with no args exits %s with usage" % rc)
    else:
        bad("attachtty no-arg rc=%s out=%r" % (rc, out[:500]))

    # Case 3: real server plus client over a unix-domain socket.
    # True-machine evidence: TMPDIR (/storage/.../tmp) bind EPERM,
    # /dev/shm bind EACCES, /tmp bind EROFS -- no filesystem path can
    # host the socket. Recipe patches both binaries so a leading '@'
    # selects the Linux abstract namespace (sun_path[0] = NUL, no file).
    # Prefer abstract; fall back to a filesystem probe for portability.
    # UNIX_PATH_MAX is 108, keep names flat and short.
    def _abstract_ok(name):
        try:
            srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                srv.bind(b"\x00" + name.encode())
                srv.close()
                return True, ""
            except OSError as exc:
                try:
                    srv.close()
                except OSError:
                    pass
                return False, str(exc)
        except Exception as exc:
            return False, str(exc)

    def _probe_socket_dir(candidates):
        notes = []
        for cand in candidates:
            if not cand:
                continue
            try:
                if not os.path.isdir(cand):
                    notes.append("%s: not-a-dir" % cand)
                    continue
                probe = os.path.join(cand, "dt-p%d.sock" % os.getpid())
                try:
                    if os.path.exists(probe):
                        os.unlink(probe)
                except OSError:
                    pass
                srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                try:
                    srv.bind(probe)
                    srv.close()
                    try:
                        os.unlink(probe)
                    except OSError:
                        pass
                    notes.append("%s: bind-ok" % cand)
                    return cand, notes
                except OSError as exc:
                    notes.append("%s: bind-fail %s" % (cand, exc))
                    try:
                        srv.close()
                    except OSError:
                        pass
                    try:
                        if os.path.exists(probe):
                            os.unlink(probe)
                    except OSError:
                        pass
                    continue
            except Exception as exc:
                notes.append("%s: error %s" % (cand, exc))
                continue
        return None, notes

    _abs_name = "hmbs-dt-%d" % os.getpid()
    _abs_ok, _abs_err = _abstract_ok(_abs_name)
    print("[test] abstract probe: %s (%s)" % ("ok" if _abs_ok else "fail", _abs_err))
    use_abstract = _abs_ok
    socket_path = None
    socket_dir = None
    if use_abstract:
        socket_path = "@" + _abs_name
        print("[test] socket path (%d chars): %s (abstract)" % (len(socket_path), socket_path))
    else:
        _cands = [tmpdir, os.environ.get("XDG_RUNTIME_DIR"), "/dev/shm"]
        try:
            _cands.append(tempfile.gettempdir())
        except Exception:
            pass
        _cands += ["/tmp"]
        # de-dup while keeping order
        _seen = set()
        _uniq = []
        for _c in _cands:
            if _c and _c not in _seen:
                _seen.add(_c)
                _uniq.append(_c)
        socket_dir, _probe_notes = _probe_socket_dir(_uniq)
        print("[test] socket probe: %s" % "; ".join(_probe_notes))
        if socket_dir is None:
            bad("no socket-capable directory among %r" % (_uniq,))
            print("RESULT: %d passed, %d failed" % (PASS, FAIL))
            print("test_package FAILED")
            return 1
        socket_path = os.path.join(socket_dir, "d-%d.sock" % os.getpid())
        if len(socket_path) >= 100:
            short = hashlib.md5(socket_dir.encode()).hexdigest()[:4]
            socket_path = os.path.join(socket_dir, "d-%s.sock" % short)
        try:
            if os.path.exists(socket_path):
                os.unlink(socket_path)
        except OSError:
            pass
        print("[test] socket dir: %s" % socket_dir)
        print("[test] socket path (%d chars): %s" % (len(socket_path), socket_path))

    # detachtty requires the child command as an absolute path.
    # Prefer system paths over harmonybrew shims for the hosted child.
    found_sleep = shutil.which("sleep")
    candidates = ["/bin/sleep", "/usr/bin/sleep"]
    if found_sleep:
        candidates.append(found_sleep)
    candidates += ["/system/bin/sleep"]
    sleep_bin = next(
        (c for c in candidates if c and os.path.isfile(c) and os.access(c, os.X_OK)),
        None,
    )
    if sleep_bin is None:
        sleep_bin = next(
            (c for c in candidates if c and os.path.isfile(c)), "/bin/sleep"
        )
    print("[test] sleep binary: %s" % sleep_bin)

    server_log = os.path.join(tmpdir, "dt-server-%d.log" % os.getpid())
    try:
        if os.path.exists(server_log):
            os.unlink(server_log)
    except OSError:
        pass
    server = None
    server_err = None
    try:
        try:
            server_err = open(server_log, "wb")
            server = subprocess.Popen(
                [detachtty, "--no-detach", socket_path, sleep_bin, "30"],
                stdout=subprocess.DEVNULL,
                stderr=server_err,
            )
        except OSError as exc:
            bad("cannot spawn detachtty server: %s" % exc)
            server = None
        if server is not None:
            ready = False
            exit_code = None
            is_abstract = socket_path.startswith("@")
            for _ in range(100):
                if not is_abstract and os.path.exists(socket_path):
                    ready = True
                    break
                exit_code = server.poll()
                if exit_code is not None:
                    break
                if is_abstract:
                    # Abstract sockets leave no file; bind failure exits
                    # fast, so survival after ~1s means serving. Keep
                    # polling a little longer for forkpty/exec startup.
                    time.sleep(0.1)
                    if _ >= 10 and server.poll() is None:
                        ready = True
                        exit_code = None
                        break
                    continue
                time.sleep(0.1)
            if not ready:
                tail = ""
                try:
                    if server_err is not None:
                        server_err.flush()
                    if os.path.isfile(server_log):
                        with open(server_log, "rb") as handle:
                            tail = handle.read().decode("utf-8", "replace")[-800:]
                except OSError:
                    pass
                bad(
                    "server socket never appeared: %s exit=%s sleep=%s log=%r"
                    % (socket_path, exit_code, sleep_bin, tail)
                )
            else:
                rc, out = run([attachtty, socket_path, "hello-detachtty", "1"], timeout=20)
                if rc == 0:
                    ok("attachtty connected to live detachtty socket (rc=0)")
                else:
                    bad("attachtty to live socket rc=%s out=%r" % (rc, out[:500]))
    finally:
        if server is not None and server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
        try:
            if server_err is not None:
                server_err.close()
        except OSError:
            pass
        try:
            if not socket_path.startswith("@") and os.path.exists(socket_path):
                os.unlink(socket_path)
        except OSError:
            pass

    print("RESULT: %d passed, %d failed" % (PASS, FAIL))
    if FAIL != 0:
        print("test_package FAILED")
        return 1
    print("test_package PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
