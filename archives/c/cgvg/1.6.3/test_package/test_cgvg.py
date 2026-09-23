#!/usr/bin/env python3
"""cgvg 1.6.3 consumer smoke test — runs the packaged scripts for real.

Executed by test_package/conanfile.py against the package bin dir. Requires a
perl 5 interpreter on PATH (cgvg runtime dependency — HarmonyOS PC provides
perl.org 5.42.0 at /data/service/hnp/bin/perl).

Flow (mirrors real cgvg usage under a shell):
  1. cg <pattern>  — recursive grep over *.c-like files, writes ~/.cgvg log
  2. cg -l         — replays the last search via the ~/.cglast symlink
  3. vg <n>        — reads the log entry and execs $EDITOR +<line> <file>
                     (fake editor proves the wiring; upstream uses vg to jump
                     vi/gvim/emacs to the match location)
A perl -c syntax check on the generated scripts is included for coverage of
the second shipped script's parser entry points.

Exit code: 0 = all assertions passed, 1 = any assertion failed.
"""
import os
import shutil
import subprocess
import sys
import tempfile


def check(cond, msg):
    if not cond:
        print(f"cgvg-smoke FAIL: {msg}", file=sys.stderr)
        sys.exit(1)


def main():
    bin_dir = sys.argv[1]
    perl = shutil.which("perl")
    check(perl is not None, "perl interpreter not found on PATH — cgvg requires perl at runtime")

    cg = os.path.join(bin_dir, "cg")
    vg = os.path.join(bin_dir, "vg")
    for exe in (cg, vg):
        check(os.path.isfile(exe), f"missing packaged script: {exe}")
        check(os.access(exe, os.X_OK), f"packaged script not executable: {exe}")
    check(os.path.isfile(os.path.join(bin_dir, "cgvg-common.pl")),
          "missing packaged data file: cgvg-common.pl")

    # perl -c syntax check on the generated scripts
    for exe in (cg, vg):
        rc = subprocess.run([perl, "-c", exe], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL).returncode
        check(rc == 0, f"perl -c failed for {exe} (rc={rc})")

    # isolated HOME + scratch project
    work = tempfile.mkdtemp(prefix="cgvg-smoke-")
    home = os.path.join(work, "home")
    os.makedirs(home)
    proj = os.path.join(work, "proj")
    os.makedirs(proj)
    with open(os.path.join(proj, "hello.c"), "w") as f:
        f.write("hello world\n")
    with open(os.path.join(proj, "Makefile"), "w") as f:
        f.write("# sample makefile\n")

    def run(exe, args, cwd, extra_env=None):
        env = dict(os.environ)
        env["HOME"] = home
        env["PWD"] = cwd
        if extra_env:
            env.update(extra_env)
        return subprocess.run([exe] + args, cwd=cwd, env=env,
                              stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=60)

    # 1) cg <pattern>: recursive grep producing a log + display
    r = run(cg, ["hello"], proj)
    out = r.stdout.decode("utf-8", "replace")
    check(r.returncode == 0, f"cg hello exited {r.returncode}:\n{out}")
    check("hello.c" in out, f"cg output misses matched file hello.c:\n{out}")
    check("hello world" in out, f"cg output misses matched line:\n{out}")
    check(os.path.islink(os.path.join(home, ".cglast")),
          "cg did not create the ~/.cglast symlink")

    # 2) cg -l: replay of the last search
    r = run(cg, ["-l"], proj)
    out = r.stdout.decode("utf-8", "replace")
    check(r.returncode == 0, f"cg -l exited {r.returncode}:\n{out}")
    check("hello.c" in out, f"cg -l replay misses hello.c:\n{out}")

    # 3) vg <n>: editor jump to the recorded file:line via a fake editor
    fakebin = os.path.join(work, "fakebin")
    os.makedirs(fakebin)
    fakevi = os.path.join(fakebin, "fakevi")
    with open(fakevi, "w") as f:
        f.write("#!/bin/sh\n")
        f.write('echo "FAKEVI-ARGS:$@"\n')
    os.chmod(fakevi, 0o755)
    path = fakebin + os.pathsep + os.environ.get("PATH", "")
    r = run(vg, ["0"], proj, extra_env={"EDITOR": "fakevi", "PATH": path})
    out = r.stdout.decode("utf-8", "replace")
    check(r.returncode == 0, f"vg 0 exited {r.returncode}:\n{out}")
    check("FAKEVI-ARGS:+1 hello.c" in out,
          f"vg 0 did not open the right file:line (got):\n{out}")

    # vg without arguments must fail with usage (error path exercised)
    r = run(vg, [], proj, extra_env={"EDITOR": "fakevi", "PATH": path})
    check(r.returncode != 0, "vg with no arguments should exit non-zero")

    print("cgvg-smoke PASS: packaged cg/vg/cgvg-common.pl verified end-to-end "
          "under %s" % perl)


if __name__ == "__main__":
    main()
