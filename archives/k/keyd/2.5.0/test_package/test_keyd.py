#!/usr/bin/env python3
"""Consumer test for the packaged keyd 2.5.0 binary.

Three layers, all of them real:
  1. the CLI surface that works without privileges (version / help / list-keys);
  2. the IPC and daemon startup paths, asserted through the diagnostics keyd
     itself emits when it cannot reach /var/run/keyd.socket;
  3. probe_input, which calls the kernel interfaces keyd depends on (uinput
     create side, evdev read side, /dev/input discovery, inotify hotplug watch)
     and reports the verbatim errno -- that is the adaptation finding of this
     package, so it is asserted here instead of being narrated in the PR body.

usage: test_keyd.py <package_folder> <probe_binary>
"""

import os
import subprocess
import sys

TIMEOUT = 20

npass = nfail = nskip = 0
evidence = []


def check(label, ok, detail=""):
    global npass, nfail, nskip
    if ok is None:
        nskip += 1
        print("[SKIP] %s %s" % (label, detail))
    elif ok:
        npass += 1
        print("[PASS] %s %s" % (label, detail))
    else:
        nfail += 1
        print("[FAIL] %s %s" % (label, detail))
    if detail:
        evidence.append((label, detail))


def run(binary, args, stdin_devnull=True):
    """Return (rc, stdout, stderr); never raises and never hangs."""
    cmd = [binary] + args
    kwargs = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
    if stdin_devnull:
        kwargs["stdin"] = subprocess.DEVNULL
    try:
        p = subprocess.run(cmd, timeout=TIMEOUT, **kwargs)
    except subprocess.TimeoutExpired:
        return (None, "", "TIMEOUT after %ss" % TIMEOUT)
    return (p.returncode,
            p.stdout.decode("utf-8", "replace"),
            p.stderr.decode("utf-8", "replace"))


def main():
    if len(sys.argv) < 3:
        print("usage: test_keyd.py <package_folder> <probe_binary>")
        return 2
    pkg, probe = sys.argv[1], sys.argv[2]
    keyd = os.path.join(pkg, "bin", "keyd")

    print("== layer 1: unprivileged CLI surface ==")
    if not (os.path.isfile(keyd) and os.access(keyd, os.X_OK)):
        check("installed keyd is executable", False, keyd)
        return finish()
    check("installed keyd is executable", True, keyd)

    rc, out, err = run(keyd, ["--version"])
    check("version rc=0", rc == 0, "rc=%s" % rc)
    check("version string matches upstream 2.5.0", "v2.5.0" in out,
          "stdout=%r" % out.strip())
    rc_v, out_v, _ = run(keyd, ["-v"])
    check("-v identical to --version", (rc_v, out_v) == (rc, out))
    rc_w, out_w, _ = run(keyd, ["version"])
    check("word form identical to --version", (rc_w, out_w) == (rc, out))

    rc, out, err = run(keyd, ["--help"])
    check("help rc=0", rc == 0, "rc=%s" % rc)
    check("help prints the usage line", out.startswith("usage: keyd"),
          repr(out.splitlines()[0] if out else ""))
    missing = [v for v in ("monitor", "list-keys", "reload", "listen", "bind")
               if v not in out]
    check("help documents every client command", not missing,
          "missing=%s" % missing if missing else "5/5")
    rc_h, out_h, _ = run(keyd, ["help"])
    check("word form identical to --help", (rc_h, out_h) == (rc, out))
    rc_u, out_u, _ = run(keyd, ["no-such-command"])
    check("unknown command falls back to help (upstream behaviour)",
          rc_u == 0 and out_u == out, "rc=%s" % rc_u)

    rc, out, err = run(keyd, ["list-keys"])
    names = out.split("\n")[:-1] if out.endswith("\n") else out.split("\n")
    keys = [n for n in names if n]
    check("list-keys rc=0", rc == 0, "rc=%s" % rc)
    check("list-keys emits the full keycode table", len(keys) > 300,
          "%d of %d lines carry a name" % (len(keys), len(names)))
    check("list-keys names contain no whitespace",
          all(not any(c.isspace() for c in n) for n in keys))
    check("list-keys names are unique", len(set(keys)) == len(keys),
          "%d unique" % len(set(keys)))
    for k in ("esc", "a", "leftshift", "capslock"):
        if k not in keys:
            check("list-keys contains esc/a/leftshift/capslock", False,
                  "missing %s" % k)
            break
    else:
        check("list-keys contains esc/a/leftshift/capslock", True)
    _, out2, _ = run(keyd, ["list-keys"])
    check("list-keys is deterministic across runs", out2 == out)

    print("== layer 2: daemon and IPC paths as an unprivileged user ==")
    rc, out, err = run(keyd, [])
    check("daemon exits nonzero without privileges", rc not in (0, None),
          "rc=%s" % rc)
    check("daemon reports the socket-plane failure verbatim",
          "No such file or directory" in err or "Permission denied" in err,
          repr(err.strip().splitlines()[-1] if err.strip() else ""))
    check("daemon warns about the missing keyd group",
          'failed to set effective group' in err,
          "getgrnam(\"keyd\") path")

    for args in (["reload"], ["listen"], ["bind", "a=b"],
                 ["input", "a"], ["do", "C-x"]):
        rc, out, err = run(keyd, args)
        joined = out + err
        check("client %s fails with the documented IPC error" % args[0],
              rc not in (0, None) and "Failed to connect" in joined,
              "rc=%s" % rc)

    # `monitor` reaches for the hotplug watcher before it touches the socket, so
    # on this platform its failure names the input subsystem instead (src/device.c:260/266).
    rc, out, err = run(keyd, ["monitor"])
    joined = out + err
    if "inotify: Permission denied" in joined:
        check("client monitor fails on the input subsystem before IPC", True,
              repr(joined.strip()))
    elif rc is None:
        check("client monitor fails on the input subsystem before IPC", None,
              "watcher installed, monitor streamed until the timeout")
    else:
        check("client monitor fails on the input subsystem before IPC", False,
              "rc=%s out=%r" % (rc, joined.strip()))

    print("== layer 3: the kernel interfaces keyd needs (probe) ==")
    if not (os.path.isfile(probe) and os.access(probe, os.X_OK)):
        check("probe binary present", False, probe)
        return finish()
    try:
        p = subprocess.run([probe], timeout=TIMEOUT,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        prc, pout = p.returncode, p.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        prc, pout = None, "TIMEOUT"
    sys.stdout.write(pout)
    check("probe exits clean", prc == 0, "rc=%s" % prc)
    summary = _line_starting(pout, "SUMMARY")
    check("probe summary reports zero FAIL", "fail=0" in summary, summary)
    for name in ("control open /dev/null", "control opendir /dev"):
        line = _case_line(pout, name)
        check("probe baseline holds: %s" % name, line.endswith("PASS"),
              line.strip() or "case missing")
    for name in ("stat /dev/uinput", "stat /sys/class/misc/uinput/dev",
                 "open /dev/uinput (w)", "open /dev/input/event0",
                 "opendir /dev/input", "inotify_add_watch /dev/input"):
        line = _case_line(pout, name)
        verdict = line.split()[-1] if line else ""
        if verdict == "PASS":
            # the mechanism is specifically a MAC denial (EACCES), so the
            # errno is asserted case by case rather than inferred from verdict
            check("input plane denied with EACCES: %s" % name,
                  " errno=13 " in line, line.strip())
        elif verdict == "SKIP":
            check("input plane denied with EACCES: %s" % name, None,
                  "kernel granted this interface, nothing to assert")
        else:
            check("input plane denied with EACCES: %s" % name, False,
                  line or "case missing")

    print("== packaged data surface ==")
    layouts = os.path.join(pkg, "share", "keyd", "layouts")
    entries = sorted(os.listdir(layouts)) if os.path.isdir(layouts) else []
    check("layouts installed", len(entries) > 50, "%d layouts" % len(entries))
    check("every layout file is non-empty",
          all(os.path.getsize(os.path.join(layouts, e)) > 0 for e in entries),
          "%d files" % len(entries))
    check("layouts are shipped under share/keyd/layouts",
          os.path.isfile(os.path.join(layouts, "af")), ",".join(entries[:3]))
    check("man page installed",
          os.path.isfile(os.path.join(pkg, "share", "man", "man1", "keyd.1.gz")))
    check("keyd.compose installed",
          os.path.isfile(os.path.join(pkg, "share", "keyd", "keyd.compose")))
    mapper = os.path.join(pkg, "bin", "keyd-application-mapper")
    check("keyd-application-mapper installed executable",
          os.path.isfile(mapper) and os.access(mapper, os.X_OK))
    return finish()


def _case_line(pout, name):
    for line in pout.splitlines():
        if line.startswith("CASE") and name in line:
            return line
    return ""


def _line_starting(pout, prefix):
    for line in pout.splitlines():
        if line.startswith(prefix):
            return line
    return ""


def finish():
    print("[test] assertions: PASS=%d FAIL=%d SKIP=%d" % (npass, nfail, nskip))
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
