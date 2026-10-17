#!/usr/bin/env python3
"""test_conmux.py — L0c-visible test source for conmux 0.12.0.

L0c requires a .c/.cpp/.py test source file in test_package/ — this .py
drives the real packaged conmux-registry via its TCP protocol and loads
the packaged Conmux.pm module (R34: real API, not print-only shell).
Scripts are invoked via `perl -I <deps> script` (toybox env shebang does
not reliably forward PERL5LIB; explicit -I is deterministic on OHOS).
Usage: test_conmux.py <conmux-registry-path> <conmux-lib-dir> [PERL5LIB]
"""
import os
import socket
import subprocess
import sys
import tempfile
import time


def _perl(conmux_lib: str, perl5lib: str) -> list:
    """Build the perl invocation prefix with explicit -I include paths."""
    perl = "/data/service/hnp/bin/perl" if os.path.isfile(
        "/data/service/hnp/bin/perl") else "perl"
    cmd = [perl, "-I", conmux_lib]
    for d in (perl5lib or "").split(":"):
        if d:
            cmd += ["-I", d]
    return cmd


def check_usage(script: str, expected: str,
                conmux_lib: str, perl5lib: str) -> None:
    """Run the packaged script (via perl -I) with no args; assert usage."""
    cmd = _perl(conmux_lib, perl5lib) + [script]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    combined = (r.stdout or "") + (r.stderr or "")
    if expected not in combined:
        raise AssertionError(
            f"{script}: usage hint missing. got: {combined[:300]}")


def conmux_cmd(sock: socket.socket, cmd: str, args: dict) -> dict:
    """Implement the conmux protocol framing (encodeArgs/sendCmd).
    args are URI-escaped key=value pairs, reply is space-split k=v."""
    from urllib.parse import quote, unquote

    def enc(d):
        return " ".join(f"{quote(str(k), safe='')}={quote(str(v), safe='')}"
                        for k, v in sorted(d.items()))

    def dec(line):
        out = {}
        for nv in line.split(" "):
            if "=" in nv:
                n, v = nv.split("=", 1)
                out[unquote(n)] = unquote(v)
        return out

    sock.sendall(f"{cmd} {enc(args)}\n".encode())
    line = sock.recv(65536).decode().strip()
    return dec(line)


def main():
    if len(sys.argv) < 3:
        raise SystemExit(
            "usage: test_conmux.py <conmux-registry-path> <conmux-lib-dir> "
            "[PERL5LIB]")
    registry_bin = sys.argv[1]
    conmux_lib = sys.argv[2]
    perl5lib = sys.argv[3] if len(sys.argv) > 3 else ""
    # conmux-attach 仅 use lib $FindBin::Bin（bin/），需经 -I 注入 lib/
    os.environ.setdefault("PERL5LIB", conmux_lib)

    # 1. scripts are runnable (usage hints emitted)
    registry_dir = os.path.dirname(registry_bin)
    check_usage(registry_bin, "Usage:", conmux_lib, perl5lib)
    check_usage(os.path.join(registry_dir, "conmux"), "Usage:",
                conmux_lib, perl5lib)
    bin_dir = os.path.join(os.path.dirname(registry_dir), "bin")
    # conmux-attach 的 usage 无 "Usage:" 前缀（格式不同）
    check_usage(os.path.join(bin_dir, "conmux-attach"), "conmux-attach:",
                conmux_lib, perl5lib)
    check_usage(os.path.join(bin_dir, "console"), "Usage:",
                conmux_lib, perl5lib)
    print("OK: packaged scripts runnable (usage hints)")

    # 2. Conmux.pm loads through the packaged lib dir (perl -I)
    r = subprocess.run(_perl(conmux_lib, perl5lib) +
                       ["-MConmux", "-e", "print 'ok'"],
                       capture_output=True, text=True, timeout=20)
    if r.returncode != 0 or "ok" not in r.stdout:
        raise AssertionError(f"Conmux.pm load failed: "
                             f"{r.stderr or r.stdout}")
    print("OK: Conmux.pm loaded from package")

    # 3. real conmux-registry protocol: start registry, ADD/LOOKUP/LIST
    store_fd, store = tempfile.mkstemp(prefix="conmux-store-")
    os.close(store_fd)
    port = 63100
    logf = tempfile.NamedTemporaryFile(prefix="conmux-reg-", suffix=".log",
                                       delete=False)
    logf.close()
    proc = subprocess.Popen(
        _perl(conmux_lib, perl5lib) + [registry_bin, str(port), store],
        stdout=open(logf.name, "w"), stderr=subprocess.STDOUT)
    try:
        deadline = time.time() + 15
        ok = False
        while time.time() < deadline:
            try:
                s = socket.create_connection(("127.0.0.1", port), timeout=2)
                ok = True
                break
            except OSError:
                time.sleep(0.3)
        if not ok:
            raise AssertionError("conmux-registry listener not reachable")
        r_add = conmux_cmd(s, "ADD", {"service": "test1",
                                      "location": "127.0.0.1:7000"})
        if r_add.get("status") != "OK":
            raise AssertionError(f"ADD failed: {r_add}")
        r_lookup = conmux_cmd(s, "LOOKUP", {"service": "test1"})
        if r_lookup.get("status") != "OK" or \
                r_lookup.get("result") != "127.0.0.1:7000":
            raise AssertionError(f"LOOKUP failed: {r_lookup}")
        r_list = conmux_cmd(s, "LIST", {})
        if r_list.get("status") != "OK":
            raise AssertionError(f"LIST failed: {r_list}")
        s.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        for p in (store, logf.name):
            try:
                os.unlink(p)
            except OSError:
                pass
    print("OK: conmux-registry protocol ADD/LOOKUP/LIST")
    print("OK: conmux 0.12.0 python-driven check")


if __name__ == "__main__":
    main()
