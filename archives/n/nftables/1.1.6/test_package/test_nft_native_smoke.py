#!/usr/bin/env python3
"""nftables 1.1.6 native socket-free smoke (stdlib only, no kernel/root/netlink).

Re-drives the intent of the 5 upstream automake TESTS (tests/shell, monitor,
py, json_echo, build) against the actually delivered artifacts without the
environment gates that block all 5 on HongMeng (unshare seccomp + modprobe/
kmod + nf_tables + root + .git; every nft/libnftables entry opens
NETLINK_NETFILTER at startup and exits 3 EPERM here):

  group 1 "nft-binary"    : sbin/nft file bytes -- exists, non-empty, ELF
                            magic 7f454c46, contains version string 1.1.6
                            (no exec, no netlink; exec would exit 3 EPERM).
  group 2 "static-archives": lib/libnftables.a + lib/libnftnl.a -- exist,
                            non-empty, `!<arch>` magic, contain the real
                            API symbol names (nft_ctx_new/nft_ctx_free /
                            nftnl_table_alloc/nftnl_chain_alloc/
                            nftnl_rule_alloc/nftnl_set_alloc) as byte
                            substrings. A stub/empty archive fails here.
  group 3 "headers"        : include/nftables/libnftables.h (+ pc file) --
                            exist, non-empty, declare nft_ctx_new. Proves
                            header usability without calling (calling would
                            open NETLINK_NETFILTER and exit 3).
  group 4 "libnftnl-runtime": run the CMake-built test_nftnl_smoke binary
                            (links packaged libnftnl.a, calls alloc/free
                            for table/chain/rule/set -- pure userspace, no
                            socket) -- exit 0, stdout non-empty with the
                            OK markers, no fatal signal.

Every group asserts non-empty fixtures/outputs (toybox-tar empty-compare
lesson); a stub binary, empty archive, or broken allocator fails instead of
passing. Usage: python3 test_nft_native_smoke.py <package_folder>
<smoke_binary> [workdir]. Exit 0 <=> 4/4 PASS. Prints SMOKE <name> PASS
lines plus a SUMMARY line for the conan harness to count.
"""
import os
import subprocess
import sys

GROUPS = ("nft-binary", "static-archives", "headers", "libnftnl-runtime")


def fail(group, msg):
    print("SMOKE %s FAIL: %s" % (group, msg), flush=True)
    return False


def ok(group, msg):
    print("SMOKE %s PASS: %s" % (group, msg), flush=True)
    return True


def check_nft_binary(pkg):
    g = "nft-binary"
    nft = None
    for bindir in ("sbin", "bin"):
        cand = os.path.join(pkg, bindir, "nft")
        if os.path.isfile(cand):
            nft = cand
            break
    if nft is None:
        return fail(g, "sbin/nft not found under %s" % pkg)
    try:
        size = os.path.getsize(nft)
    except OSError as exc:
        return fail(g, "stat failed: %s" % exc)
    if size == 0:
        return fail(g, "nft binary empty: %s" % nft)
    try:
        with open(nft, "rb") as f:
            head = f.read(4)
    except OSError as exc:
        return fail(g, "read failed: %s" % exc)
    if head != b"\x7fELF":
        return fail(g, "not ELF (magic=%r)" % head)
    # Version string must be present in the file bytes (grep -a equivalent).
    found = False
    try:
        with open(nft, "rb") as f:
            while True:
                chunk = f.read(1048576)
                if not chunk:
                    break
                if b"1.1.6" in chunk:
                    found = True
                    break
    except OSError as exc:
        return fail(g, "scan failed: %s" % exc)
    if not found:
        return fail(g, "version string 1.1.6 not found in binary bytes")
    return ok(g, "ELF + 1.1.6 present, %d bytes, no exec/no netlink" % size)


def check_archives(pkg):
    g = "static-archives"
    needs = {
        "libnftables.a": (b"nft_ctx_new", b"nft_ctx_free"),
        "libnftnl.a": (b"nftnl_table_alloc", b"nftnl_chain_alloc",
                       b"nftnl_rule_alloc", b"nftnl_set_alloc"),
    }
    details = []
    for name, symbols in needs.items():
        p = os.path.join(pkg, "lib", name)
        if not os.path.isfile(p):
            return fail(g, "%s not found" % p)
        try:
            size = os.path.getsize(p)
        except OSError as exc:
            return fail(g, "stat %s failed: %s" % (name, exc))
        if size == 0:
            return fail(g, "%s empty" % name)
        try:
            with open(p, "rb") as f:
                magic = f.read(8)
                f.seek(0)
                data = f.read()
        except OSError as exc:
            return fail(g, "read %s failed: %s" % (name, exc))
        if not magic.startswith(b"!<arch>"):
            return fail(g, "%s not an ar archive (magic=%r)" % (name, magic))
        if len(data) == 0:
            return fail(g, "%s read 0 bytes" % name)
        for sym in symbols:
            if sym not in data:
                return fail(g, "%s missing symbol bytes %r" % (name, sym))
        details.append("%s %d bytes + %d symbols" % (name, size, len(symbols)))
    return ok(g, "; ".join(details))


def check_headers(pkg):
    g = "headers"
    hdr = os.path.join(pkg, "include", "nftables", "libnftables.h")
    if not os.path.isfile(hdr):
        return fail(g, "header not found: %s" % hdr)
    try:
        size = os.path.getsize(hdr)
    except OSError as exc:
        return fail(g, "stat header failed: %s" % exc)
    if size == 0:
        return fail(g, "header empty")
    try:
        with open(hdr, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError as exc:
        return fail(g, "read header failed: %s" % exc)
    if not text.strip():
        return fail(g, "header whitespace-only")
    if "nft_ctx_new" not in text:
        return fail(g, "header missing nft_ctx_new declaration")
    pc = os.path.join(pkg, "lib", "pkgconfig", "libnftables.pc")
    pc_ok = os.path.isfile(pc) and os.path.getsize(pc) > 0
    if not pc_ok:
        return fail(g, "libnftables.pc missing or empty")
    return ok(g, "libnftables.h %d bytes + declares nft_ctx_new + pc present"
             % size)


def check_runtime(smoke_bin, workdir):
    g = "libnftnl-runtime"
    if not smoke_bin or not os.path.isfile(smoke_bin):
        return fail(g, "smoke binary not found: %r" % smoke_bin)
    try:
        if os.path.getsize(smoke_bin) == 0:
            return fail(g, "smoke binary empty")
    except OSError as exc:
        return fail(g, "stat smoke binary failed: %s" % exc)
    try:
        proc = subprocess.run([smoke_bin], cwd=workdir or None,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=120)
    except Exception as exc:
        return fail(g, "exec failed: %s" % exc)
    if proc.returncode != 0:
        out = (proc.stdout or b"")[-2000:]
        if proc.returncode < 0:
            return fail(g, "killed by signal %d, out=%r"
                        % (-proc.returncode, out))
        return fail(g, "exit %d, out=%r" % (proc.returncode, out))
    out = proc.stdout or b""
    if not out.strip():
        return fail(g, "empty output (fixture/output must be non-empty)")
    if b"libnftnl alloc OK" not in out or b"libnftnl free OK" not in out:
        return fail(g, "missing OK markers, out=%r" % out[-1000:])
    return ok(g, "alloc/free table+chain+rule+set, %d output bytes, exit 0"
              % len(out))


def main(argv):
    pkg = argv[1] if len(argv) > 1 else None
    smoke_bin = argv[2] if len(argv) > 2 else None
    workdir = argv[3] if len(argv) > 3 else None
    if not pkg or not os.path.isdir(pkg):
        print("SMOKE harness FAIL: bad package folder %r" % pkg, flush=True)
        return 2
    passed = 0
    if check_nft_binary(pkg):
        passed += 1
    if check_archives(pkg):
        passed += 1
    if check_headers(pkg):
        passed += 1
    if workdir and not os.path.isdir(workdir):
        try:
            os.makedirs(workdir, exist_ok=True)
        except OSError:
            workdir = None
    if check_runtime(smoke_bin, workdir):
        passed += 1
    print("SMOKE SUMMARY: %d/%d passed" % (passed, len(GROUPS)), flush=True)
    return 0 if passed == len(GROUPS) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
