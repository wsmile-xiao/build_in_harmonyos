#!/usr/bin/env python3
"""Consumer test for the daemontools-encore Conan package.

Every check runs a packaged command line tool against real input and asserts
the behaviour documented by upstream (``rts.tests/*.exp`` semantics, but driven
from Python so that no extra shell is required):

  envdir, envini, fghack, pgrphack, setlock, softlimit, tai64n, tai64nlocal,
  multilog (log directory + status file), svstat, svc, svok, supervise.

The supervise family needs ``mkfifo(2)`` for supervise's control channel.  The
script probes that capability first: when FIFOs are available it runs a real
supervise/svok/svstat/svc cycle; when they are not (HarmonyOS PC denies FIFO
creation to user processes, knowledge entry E074) it asserts that supervise
still reports the documented control-channel error instead of crashing or
hanging, and that the client tools (svstat/svc/svok) keep their documented exit
codes for unsupervised and nonexistent service directories.

The script executes 31 assertions on a device that denies FIFO creation (the
capability probe then asserts the documented control-channel error). A PASSING run on
a FIFO-capable platform executes exactly 34 assertions (the probe instead runs the real
supervise cycle). A failing capable-platform run reports 32, 33 or 34: a replaced record
lowers the total, while a failure recorded in addition to the four records keeps it at 34
(all three observed with stubs, see reports/capable-branch-stub-test.log.md).

Usage: test_daemontools.py <package bin directory>
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

BIN = os.path.abspath(sys.argv[1])
PY = sys.executable
RESULTS = []


def record(name, ok, detail=""):
    RESULTS.append((name, ok))
    status = "PASS" if ok else "FAIL"
    line = f"{status}  {name}"
    if detail:
        line += f"  |  {detail}"
    print(line, flush=True)


def run(args, **kwargs):
    return subprocess.run(args, capture_output=True, text=True, errors="replace", **kwargs)


def check(name, args, expect_rc=0, contains=None, regex=None, **kwargs):
    proc = run(args, **kwargs)
    out = (proc.stdout or "") + (proc.stderr or "")
    ok = proc.returncode == expect_rc
    if ok and contains is not None:
        needles = contains if isinstance(contains, (list, tuple)) else [contains]
        ok = all(n in out for n in needles)
    if ok and regex is not None:
        ok = re.search(regex, out, re.M) is not None
    record(name, ok, f"rc={proc.returncode} out={out.strip()[:140]!r}")
    return proc


def write(path, text, mode=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    if mode is not None:
        os.chmod(path, mode)
    return path


def main():
    work = tempfile.mkdtemp(prefix="daemontools-test-", dir=os.getcwd())
    print(f"[info] bin dir : {BIN}")
    print(f"[info] work dir: {work}")

    tools = ("envdir", "envini", "envuidgid", "fghack", "multilog", "pgrphack",
             "readproctitle", "setlock", "setuidgid", "setuser", "softlimit",
             "supervise", "svc", "svok", "svscan", "svscanboot", "svstat", "svup",
             "tai64n", "tai64nlocal")
    missing = [t for t in tools if not os.access(os.path.join(BIN, t), os.X_OK)]
    record("package ships the 20 upstream programs", not missing,
           f"missing={missing}" if missing else f"{len(tools)} programs executable")

    # ---------------------------------------------------------------- envdir
    env1 = os.path.join(work, "env1")
    write(os.path.join(env1, "Message"), "This is a test. This is only a test.\n")
    write(os.path.join(env1, "EMPTY"), "")
    proc = check("envdir sets variables from the directory",
                 [os.path.join(BIN, "envdir"), env1, PY, "-c",
                  "import os;print(os.environ.get('Message','<unset>'))"],
                 contains="This is a test. This is only a test.")
    env2 = os.path.join(work, "env2")
    write(os.path.join(env2, "Message"), "")
    check("envdir removes variables whose file is empty",
          [os.path.join(BIN, "envdir"), env1, os.path.join(BIN, "envdir"), env2, PY, "-c",
           "import os;print('[%s]' % os.environ.get('Message','<unset>'))"],
          contains="[<unset>]")
    check("envdir -p prefixes variables",
          [os.path.join(BIN, "envdir"), "-p", "prefix_", env1, PY, "-c",
           "import os;print(os.environ.get('prefix_Message','<unset>'))"],
          contains="This is a test. This is only a test.")
    check("envdir reports usage on missing arguments",
          [os.path.join(BIN, "envdir")], expect_rc=111, contains="usage: envdir")

    # ---------------------------------------------------------------- envini
    inifile = os.path.join(work, "envi")
    write(inifile, "; comment\nbroken\n Message = This is a test.\n[sect]\n"
                   "Message=This is only a test.    \n")
    check("envini reads global and section variables",
          [os.path.join(BIN, "envini"), inifile, PY, "-c",
           "import os;print(os.environ.get('Message','<unset>'));"
           "print(os.environ.get('sect_Message','<unset>'))"],
          contains=["This is a test.", "This is only a test."])
    check("envini -p prefixes global variables",
          [os.path.join(BIN, "envini"), "-p", "prefix_", inifile, PY, "-c",
           "import os;print(os.environ.get('prefix_Message','<unset>'))"],
          contains="This is a test.")

    # -------------------------------------------------------- fghack/pgrphack
    check("fghack runs its child and keeps stdout connected",
          [os.path.join(BIN, "fghack"), PY, "-c", "print('fghack-child-ran')"],
          contains="fghack-child-ran")
    check("fghack reports usage on missing arguments",
          [os.path.join(BIN, "fghack")], expect_rc=100, contains="usage: fghack")
    check("pgrphack runs its child and it reports its own process group id",
          [os.path.join(BIN, "pgrphack"), PY, "-c",
           "import os;print('child-pgrp=%d' % os.getpgrp())"],
          regex=r"child-pgrp=(\d+)")
    parent_pgrp = os.getpgrp()
    child = run([os.path.join(BIN, "pgrphack"), PY, "-c", "import os;print(os.getpgrp())"])
    child_out = (child.stdout or "").strip()
    # No fallback value here: an empty/garbled child output is a failure, not a pass.
    child_pgrp = int(child_out) if child_out.isdigit() else None
    record("pgrphack really leaves the caller's process group",
           child.returncode == 0 and child_pgrp is not None and child_pgrp != parent_pgrp,
           f"rc={child.returncode} caller pgrp={parent_pgrp} child pgrp={child_pgrp}")

    # ---------------------------------------------------------------- setlock
    lockfile = os.path.join(work, "lock")
    check("setlock runs the child while holding the lock file",
          [os.path.join(BIN, "setlock"), lockfile, PY, "-c", "print('lock-held')"],
          contains="lock-held")
    record("setlock creates the lock file", os.path.isfile(lockfile), lockfile)
    inner = ("import subprocess,sys;"
             "p=subprocess.run([sys.argv[1],'-n',sys.argv[2],sys.argv[3],'-c','print(\"inner\")'],"
             "capture_output=True,text=True);"
             "print('inner-rc=%d' % p.returncode);print((p.stdout+p.stderr).strip())")
    proc = check("setlock -n fails while the lock is already held",
                 [os.path.join(BIN, "setlock"), lockfile, PY, "-c", inner,
                  os.path.join(BIN, "setlock"), lockfile, PY],
                 contains=["inner-rc=111", "unable to lock"])
    inner_x = inner.replace("'-n'", "'-nx'").replace("inner-rc", "innerx-rc")
    check("setlock -nx exits quietly while the lock is already held",
          [os.path.join(BIN, "setlock"), lockfile, PY, "-c", inner_x,
           os.path.join(BIN, "setlock"), lockfile, PY],
          contains=["innerx-rc=0"])

    # -------------------------------------------------------------- softlimit
    proc = check("softlimit -c 0 lowers the child core limit",
                 [os.path.join(BIN, "softlimit"), "-c", "0", PY, "-c",
                  "import resource;print('core=%d' % resource.getrlimit(resource.RLIMIT_CORE)[0])"],
                 contains="core=0")
    check("softlimit passes the child through unchanged otherwise",
          [os.path.join(BIN, "softlimit"), "-p", "0", PY, "-c", "print('softlimit-child-ran')"],
          contains="softlimit-child-ran")

    # ---------------------------------------------------------------- tai64n
    proc = check("tai64n stamps every line with a 12 byte TAI64N label",
                 [os.path.join(BIN, "tai64n")], expect_rc=0,
                 regex=r"^@[0-9a-f]{24} ONE$", input="ONE\nTWO\n")
    stamps = re.findall(r"^(@[0-9a-f]{24}) ", proc.stdout or "", re.M)
    record("tai64n labels two lines", len(stamps) == 2, f"labels={len(stamps)}")
    proc = check("tai64nlocal converts TAI64N lines back to local time",
                 [os.path.join(BIN, "tai64nlocal")], expect_rc=0,
                 regex=r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+ ONE$",
                 input=proc.stdout)
    check("tai64nlocal passes non-stamped lines through",
          [os.path.join(BIN, "tai64nlocal")], expect_rc=0, contains="plain-line",
          input="plain-line\n")

    # --------------------------------------------------------------- multilog
    logdir = os.path.join(work, "log")
    os.makedirs(logdir, exist_ok=True)
    proc = run([os.path.join(BIN, "multilog"), "t", logdir], input="line-a\nline-b\n")
    current = os.path.join(logdir, "current")
    body = open(current, encoding="utf-8", errors="replace").read() if os.path.isfile(current) else ""
    record("multilog writes timestamped lines into dir/current",
           proc.returncode == 0 and re.search(r"^@[0-9a-f]{24} line-a$", body, re.M)
           and re.search(r"^@[0-9a-f]{24} line-b$", body, re.M),
           f"rc={proc.returncode} current={body.strip()[:120]!r}")
    status = os.path.join(work, "status-file")
    proc = run([os.path.join(BIN, "multilog"), f"={status}"], input="one\ntwo\n")
    data = open(status, "rb").read() if os.path.isfile(status) else b""
    # multilog's status action keeps a fixed 1001 byte record: the last line
    # ("two") followed by the 997 unused newline slots of its line buffer.
    record("multilog =status keeps the fixed status record",
           proc.returncode == 0 and len(data) == 1001 and data.count(b"\n") == 998
           and b"two" in data,
           f"rc={proc.returncode} bytes={len(data)} newlines={data.count(chr(10).encode())}")
    proc = run([os.path.join(BIN, "multilog"), "e"], input="err-line\n")
    record("multilog e forwards matched lines to stderr",
           proc.returncode == 0 and "err-line" in (proc.stderr or ""),
           f"rc={proc.returncode} stderr={(proc.stderr or '').strip()[:80]!r}")
    check("readproctitle reports usage on missing arguments",
          [os.path.join(BIN, "readproctitle")], expect_rc=100)

    # ---------------------------------------- supervise client tools (no FIFO)
    svdir = os.path.join(work, "test.sv")
    os.makedirs(svdir, exist_ok=True)
    check("svok reports 100 for an existing but unsupervised directory",
          [os.path.join(BIN, "svok"), svdir], expect_rc=100)
    check("svok reports 111 for a nonexistent directory",
          [os.path.join(BIN, "svok"), os.path.join(work, "nonexistent")],
          expect_rc=111, contains="unable to chdir to")
    check("svstat reports an unsupervised service and a missing directory",
          [os.path.join(BIN, "svstat"), svdir, os.path.join(work, "nonexistent")],
          expect_rc=0, contains=["unable to open supervise/ok", "unable to chdir"])
    check("svc warns about an unsupervised service and a missing directory",
          [os.path.join(BIN, "svc"), svdir, os.path.join(work, "nonexistent")],
          expect_rc=0, contains=["unable to control", "unable to chdir"])
    check("supervise reports a missing service directory",
          [os.path.join(BIN, "supervise"), os.path.join(work, "nonexistent")],
          expect_rc=111, contains="unable to chdir to")

    # ------------------------------------------- supervise capability probe
    fifo_probe = os.path.join(work, "fifo-probe")
    fifo_supported = False
    try:
        os.mkfifo(fifo_probe, 0o600)
        fifo_supported = True
    except OSError as exc:
        print(f"[info] mkfifo(2) unavailable on this platform: {exc}")
    if os.path.exists(fifo_probe):
        os.unlink(fifo_probe)

    write(os.path.join(svdir, "run"), "#!/bin/sh\nexec sleep 1000\n", 0o755)
    proc = None
    up = False
    stopped = False
    try:
        if fifo_supported:
            proc = subprocess.Popen([os.path.join(BIN, "supervise"), svdir],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            # svok only proves that the control channel exists, so the up check uses
            # svup's exit code, exactly like upstream's own rts suite (`waituntil svup`).
            for _ in range(50):
                if run([os.path.join(BIN, "svok"), svdir]).returncode == 0:
                    up = True
                    break
                time.sleep(0.2)
            record("supervise comes up and svok reports the service as supervised", up)
            if not up:
                record("supervise controls its service while mkfifo(2) is available", False,
                       "svok never reported the service as supervised")
            else:
                running = False
                for _ in range(50):
                    if run([os.path.join(BIN, "svup"), svdir]).returncode == 0:
                        running = True
                        break
                    time.sleep(0.2)
                record("svup reports the service as up once supervise started it", running)
                stop = run([os.path.join(BIN, "svc"), "-x", svdir])
                record("svc -x stops the service", stop.returncode == 0, f"rc={stop.returncode}")
                stopped = stop.returncode == 0
        else:
            proc = run([os.path.join(BIN, "supervise"), svdir], timeout=30)
            out = (proc.stdout or "") + (proc.stderr or "")
            record("supervise fails fast with the documented control-channel error "
                   "(mkfifo unavailable)",
                   proc.returncode == 111 and "unable to read supervise/control" in out,
                   f"rc={proc.returncode} out={out.strip()[:140]!r}")
    except subprocess.TimeoutExpired:
        record("supervise returns instead of hanging while the control FIFO is missing", False,
               "timeout")
    finally:
        # Never leave a supervise process behind: on the FIFO-capable branch it is
        # still running after svc -x, and on a failure above it may never have come up.
        # Wording stays accurate for both paths and TERM precedes KILL so supervise
        # can stop its service itself. Every record below is a failure report, so a
        # PASSING capable-branch run always reports the same 34 assertions: a run that
        # skips one of them has already recorded a failure (32 or 33 assertions).
        if isinstance(proc, subprocess.Popen):
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=10)
                    record("supervise exits once the service is stopped" if up
                           else "supervise exits on request when it never came up", False,
                           "supervise still running, killed")
                else:
                    record("supervise exits once the service is stopped" if up
                           else "supervise exits on request when it never came up", False,
                           "supervise exited only after SIGTERM")
            else:
                if up and stopped:
                    # Upstream rts.tests/supervise-base.exp documents this exact
                    # transition: once `svc -x` has stopped the service and supervise
                    # exited, svstat reports "supervise not running" - not "down".
                    after = run([os.path.join(BIN, "svstat"), svdir])
                    text = (after.stdout or "") + (after.stderr or "")
                    record("svstat reports supervise not running after svc -x",
                           "supervise not running" in text, text.strip())

    shutil.rmtree(work, ignore_errors=True)

    total = len(RESULTS)
    failed = [name for name, ok in RESULTS if not ok]
    print(f"\nTOTAL={total} PASS={total - len(failed)} FAIL={len(failed)}")
    if failed:
        for name in failed:
            print(f"  FAILED: {name}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
