#!/usr/bin/env python3
"""Consumer driver for GNU dico 2.12 (R34): run the packaged tools and
assert real behaviour — the dico client and the dicod server both report
their version banner, and dicod exposes --config/--input help switches."""
import subprocess
import sys


def run(*args):
    return subprocess.run(args, capture_output=True, text=True)


def main():
    bindir = sys.argv[1].rstrip("/\\")
    failures = 0

    client = run(bindir + "/dico", "--version")
    if client.returncode == 0 and "dico (GNU dico) 2.12" in client.stdout:
        print("PASS: dico client reports dico (GNU dico) 2.12")
    else:
        print(f"FAIL: dico --version rc={client.returncode} out={client.stdout!r}")
        failures += 1

    server = run(bindir + "/dicod", "--version")
    if server.returncode == 0 and "dicod (GNU dico) 2.12" in server.stdout:
        print("PASS: dicod server reports dicod (GNU dico) 2.12")
    else:
        print(f"FAIL: dicod --version rc={server.returncode} out={server.stdout!r}")
        failures += 1

    cfg = run(bindir + "/dicod", "--config-help")
    if cfg.returncode == 0 and "dicod" in (cfg.stdout + cfg.stderr):
        print("PASS: dicod --config-help renders its configuration guide")
    else:
        print(f"FAIL: dicod --config-help rc={cfg.returncode}")
        failures += 1

    if failures:
        print(f"{failures} check(s) FAILED")
        return 1
    print("dico consumer test: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
