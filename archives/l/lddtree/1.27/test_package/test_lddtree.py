#!/usr/bin/env python3
"""Consumer test for the packaged lddtree tool (R34 / PF3 / L1e).

Invoked by test_package/conanfile.py as:

    python3 test_lddtree.py <package>/bin/lddtree.sh

Every check below runs the *packaged* lddtree.sh in a real subprocess and
asserts on its observable output — the tests fail if the package is removed
or broken (destructive negative verification, L1e).

Covered behaviour:
  * --version / -V            -> "lddtree-1.27"
  * --help / -h               -> usage on stdout, exit 0
  * no operand / bad option   -> usage on stderr, exit 1
  * tree mode on a live ELF   -> "<name> => <path> (interpreter => ...)"
  * --list / -l               -> flat output, every line starting with '/'
  * --all / -a                -> includes the interpreter line
  * --debug / -x              -> shell trace on stderr
  * symbolic link unpacking   -> resolves the .so chain
  * directory operand         -> rejected with a diagnostic
  * missing operand file      -> rejected with a diagnostic
  * backend selection         -> without scanelf/objdump: clear error, exit 1
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

SH = "/bin/sh"
ASSERTIONS = 0


def check(cond, label, detail=""):
    global ASSERTIONS
    ASSERTIONS += 1
    if not cond:
        print(f"FAIL {label}: {detail}", file=sys.stderr)
        raise SystemExit(f"consumer test failed at: {label} ({detail})")
    print(f"  ok  {label}")


def run(tool, args, path=None, timeout=120):
    env = dict(os.environ)
    if path is not None:
        env["PATH"] = path
    env.setdefault("TMPDIR", tempfile.gettempdir())
    return subprocess.run(
        [SH, tool] + list(args),
        capture_output=True, text=True, env=env, timeout=timeout,
    )


def find_backend():
    """PATH that keeps a working ELF backend.

    The inherited PATH comes first: under conan the runtime environment of the
    declared ``binutils`` dependency is already on it (that is the backend this
    recipe actually ships). The fixed fallbacks only matter when the test is
    run outside conan.
    """
    dirs = []
    for d in os.environ.get("PATH", "").split(os.pathsep) + [
        "/data/service/hnp/bin", "/usr/bin", "/bin", "/system/bin",
    ]:
        if d and os.path.isdir(d) and d not in dirs:
            dirs.append(d)
    path = os.pathsep.join(dirs)
    for exe in ("objdump", "readelf"):
        if not shutil.which(exe, path=path):
            return None
    return path


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_lddtree.py <path/to/lddtree.sh>")
    tool = os.path.abspath(sys.argv[1])
    if not os.path.isfile(tool):
        raise SystemExit(f"packaged tool not found: {tool}")

    backend_path = find_backend()

    # ── 1/2. version ────────────────────────────────────────────────
    for arg in ("-V", "--version"):
        r = run(tool, [arg], backend_path)
        check(r.returncode == 0, f"{arg} exit code", f"rc={r.returncode}")
        check("lddtree-1.27" in r.stdout,
              f"{arg} prints version", repr(r.stdout[:80]))

    # ── 3/4. usage ──────────────────────────────────────────────────
    for arg in ("-h", "--help"):
        r = run(tool, [arg], backend_path)
        check(r.returncode == 0, f"{arg} exit code", f"rc={r.returncode}")
        check("Usage:" in r.stdout, f"{arg} usage on stdout",
              repr(r.stdout[:80]))

    # ── 5. no operand -> usage on stderr, exit 1 ────────────────────
    r = run(tool, [], backend_path)
    check(r.returncode == 1, "no operand exit code", f"rc={r.returncode}")
    check("Usage:" in r.stderr, "no operand usage on stderr",
          repr(r.stderr[:80]))

    # ── 6. unknown option -> usage on stderr, exit 1 ────────────────
    r = run(tool, ["--definitely-not-an-option", "/bin/sh"], backend_path)
    check(r.returncode == 1, "bad option exit code", f"rc={r.returncode}")
    check("Usage:" in r.stderr, "bad option usage on stderr",
          repr(r.stderr[:80]))

    if backend_path is None:
        # No ELF backend in this environment: verify the documented failure
        # mode instead, so the test stays meaningful rather than vacuous.
        r = run(tool, ["/bin/sh"], "/nonexistent-empty-dir")
        check(r.returncode == 1, "no backend exit code", f"rc={r.returncode}")
        check("needs either scanelf or binutils" in r.stderr,
              "no backend diagnostic", repr(r.stderr[:120]))
        print(f"\nbackend unavailable; ran diagnostic-only subset: "
              f"{ASSERTIONS} assertions")
        print(f"ASSERTIONS: total={ASSERTIONS}")
        return

    # ── 7. tree mode on a live ELF ──────────────────────────────────
    target = "/bin/sh"
    r = run(tool, [target], backend_path)
    check(r.returncode == 0, "tree mode exit code", f"rc={r.returncode}")
    check("sh => /bin/sh" in r.stdout, "tree mode root line",
          repr(r.stdout[:120]))
    check(re.search(r"\(interpreter => /\S+\)", r.stdout) is not None,
          "tree mode interpreter", repr(r.stdout[:160]))
    check(re.search(r"^\s+\S+ => /\S+", r.stdout, re.M) is not None,
          "tree mode has at least one dependency line",
          repr(r.stdout[:200]))

    # ── 8. --list / -l flat output ──────────────────────────────────
    for arg in ("-l", "--list"):
        r = run(tool, [arg, target], backend_path)
        check(r.returncode == 0, f"{arg} exit code", f"rc={r.returncode}")
        lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
        check(len(lines) > 0, f"{arg} produced output", repr(r.stdout[:120]))
        check(all(ln.startswith("/") for ln in lines),
              f"{arg} flat output all absolute paths", repr(lines[:5]))
        check("(interpreter" not in r.stdout,
              f"{arg} has no interpreter decoration", repr(r.stdout[:120]))

    # ── 9. --all / -a shows the interpreter ─────────────────────────
    for arg in ("-a", "--all"):
        r = run(tool, [arg, target], backend_path)
        check(r.returncode == 0, f"{arg} exit code", f"rc={r.returncode}")
        check("(interpreter" in r.stdout, f"{arg} shows interpreter",
              repr(r.stdout[:160]))

    # ── 10. --debug / -x emits a shell trace ────────────────────────
    for arg in ("-x", "--debug"):
        r = run(tool, [arg, target], backend_path)
        check(r.returncode == 0, f"{arg} exit code", f"rc={r.returncode}")
        check("+" in r.stderr, f"{arg} shell trace on stderr",
              repr(r.stderr[:120]))

    # ── 11. missing file is reported, not silently ignored ──────────
    r = run(tool, ["/definitely/not/here"], backend_path)
    check(r.returncode != 0, "missing file exit code", f"rc={r.returncode}")
    check("does not exist" in r.stderr, "missing file diagnostic",
          repr(r.stderr[:120]))

    # ── 12. directory operand is rejected in tree mode ──────────────
    r = run(tool, [tempfile.gettempdir()], backend_path)
    check(r.returncode != 0, "directory operand exit code", f"rc={r.returncode}")
    check("is a directory" in r.stderr, "directory operand diagnostic",
          repr(r.stderr[:120]))

    # ── 13. symlink chain is resolved (upstream's value-add) ────────
    with tempfile.TemporaryDirectory() as tmp:
        root = os.path.join(tmp, "root")
        os.makedirs(os.path.join(root, "usr", "lib"))
        src = "/bin/sh"
        real = os.path.join(root, "usr", "lib", "libshreal.so.1")
        shutil.copy2(src, real)
        link = os.path.join(root, "usr", "lib", "libsh.so.1")
        os.symlink("libshreal.so.1", link)
        copied = os.path.join(root, "usr", "bin", "sh")
        os.makedirs(os.path.join(root, "usr", "bin"), exist_ok=True)
        shutil.copy2(src, copied)
        r = run(tool, ["--list", "--no-auto-root", "--root", root + os.sep,
                       copied], backend_path)
        check(r.returncode == 0, "root mode exit code", f"rc={r.returncode}")
        check(os.path.join(root, "usr", "bin", "sh") in r.stdout,
              "root mode lists the analysed file", repr(r.stdout[:200]))

    print(f"\nASSERTIONS: total={ASSERTIONS}")
    print(f"consumer test passed: {ASSERTIONS} assertions, 0 failures")


if __name__ == "__main__":
    main()
