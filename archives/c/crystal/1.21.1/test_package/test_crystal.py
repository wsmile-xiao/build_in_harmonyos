#!/usr/bin/env python3
"""Crystal consumer test (R34).

The package under test is a self-hosting compiler, so a print-only stub proves
nothing.  This test really compiles a program with the installed compiler and
then executes the produced binary, which is the only way to catch the two
failure modes that dominate this platform: an unsigned executable refusing to
run (EACCES), and a compiler that emits gnu-targeted code referencing
glibc-only symbols.
"""
import os
import re
import subprocess
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    crystal = os.path.join(pkg, "bin", "crystal")
    shards = os.path.join(pkg, "bin", "shards")
    for p in (crystal, shards):
        if not os.path.isfile(p):
            print("FAIL: missing installed binary %s" % p, file=sys.stderr)
            return 1
        # .codesign must be present, else the OS refuses to exec it
        out = subprocess.run(["llvm-readelf", "-S", p], capture_output=True,
                             text=True)
        if out.returncode != 0:
            print("FAIL: llvm-readelf rc=%d for %s\n%s"
                  % (out.returncode, p, (out.stderr or out.stdout)[:300]),
                  file=sys.stderr)
            return 1
        if "codesign" not in out.stdout:
            print("FAIL: %s has no .codesign section (execve would EACCES)"
                  % p, file=sys.stderr)
            return 1
        print("OK: %s carries a .codesign section" % os.path.basename(p))

    env = dict(os.environ)
    env.setdefault("CRYSTAL_PATH", os.path.join(pkg, "share", "crystal", "src"))

    # 1) the compiler runs and reports the expected version
    r = subprocess.run([crystal, "--version"], capture_output=True, text=True,
                       env=env, timeout=120)
    if r.returncode != 0 or "Crystal" not in (r.stdout + r.stderr):
        print("FAIL: crystal --version rc=%d\n%s" % (r.returncode,
                                                     (r.stderr or r.stdout)[:400]),
              file=sys.stderr)
        return 1
    blob = r.stdout + r.stderr
    m = re.search(r"Crystal\s+([0-9]+\.[0-9]+\.[0-9]+)", blob)
    if not m or m.group(1) != "1.21.1":
        print("FAIL: unexpected version string: %r" % blob[:200], file=sys.stderr)
        return 1
    print("OK: crystal --version reports %s" % m.group(1))

    # 2) really compile a program, then run the produced binary
    work = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_build")
    os.makedirs(work, exist_ok=True)
    src = os.path.join(work, "hello.cr")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write('puts "crystal-hello-ok"\n')
    exe = os.path.join(work, "hello")
    r = subprocess.run([crystal, "build", src, "-o", exe,
                        "--target", "aarch64-unknown-linux-musl"],
                       capture_output=True, text=True, env=env, timeout=600)
    if r.returncode != 0 or not os.path.isfile(exe):
        print("FAIL: compile failed rc=%d\n%s" % (r.returncode,
                                                  (r.stderr or r.stdout)[:600]),
              file=sys.stderr)
        return 1
    print("OK: crystal compiled hello.cr -> aarch64-unknown-linux-musl")

    signed = exe + ".signed"
    # The produced binary must be signed before it can be exec'd, so a failing
    # binary-sign-tool is fatal - checking only for the output file would let a
    # stale/half-written file slip through and produce a confusing EACCES later.
    r_sign = subprocess.run(["binary-sign-tool", "sign", "-inFile", exe,
                             "-outFile", signed, "-selfSign", "1"],
                            capture_output=True, text=True)
    if r_sign.returncode != 0:
        print("FAIL: binary-sign-tool rc=%d\n%s"
              % (r_sign.returncode, (r_sign.stderr or r_sign.stdout)[:400]),
              file=sys.stderr)
        return 1
    if not os.path.isfile(signed):
        print("FAIL: binary-sign-tool reported success but produced no %s"
              % signed, file=sys.stderr)
        return 1
    os.replace(signed, exe)
    os.chmod(exe, 0o755)
    r = subprocess.run([exe], capture_output=True, text=True, env=env, timeout=120)
    if r.returncode != 0 or "crystal-hello-ok" not in r.stdout:
        print("FAIL: produced binary did not run: rc=%d out=%r err=%r"
              % (r.returncode, r.stdout[:200], r.stderr[:300]), file=sys.stderr)
        return 1
    print("OK: compiled binary executed and printed %r" % r.stdout.strip())
    print("OK: crystal compiler builds and runs programs on OHOS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
