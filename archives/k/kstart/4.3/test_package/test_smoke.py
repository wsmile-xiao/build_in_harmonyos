#!/usr/bin/env python3
import subprocess


def _capture(cmd, env, timeout=30):
    proc = subprocess.run(
        cmd,
        env=env,
        timeout=timeout,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
    )
    return proc.returncode, proc.stdout or ""


def run_smoke_checks(k5start, krenew, env):
    checks = []

    rc, out = _capture([k5start, "-h"], env)
    checks.append((
        "k5start -h prints usage",
        rc == 0 and ("Usage" in out or "usage" in out),
    ))

    rc, out = _capture([krenew, "-h"], env)
    checks.append((
        "krenew -h prints usage",
        rc == 0 and ("Usage" in out or "usage" in out),
    ))

    rc, _ = _capture([k5start], env)
    checks.append(("k5start bare rc==1", rc == 1))

    rc, _ = _capture([krenew], env)
    checks.append(("krenew bare rc==1", rc == 1))

    return checks
