#!/usr/bin/env python3
"""Conan test_package for turnstile 0.1.11 (R34 degraded check).

turnstile ships a daemon (turnstiled) plus a PAM module
(pam_turnstile.so). Running the daemon needs a /run base directory and
a PAM session — neither exists on OHOS build nodes. Additionally the
release-built binary in the conan cache is rejected by the OHOS
hmmac/exec security policy with EPERM on this node (verified: a
debugoptimized build of the same source in the work dir executes and
stops at the RUN_PATH check, rc=1; the cached release binary is refused
with "Operation not permitted" even after copying to a runnable dir;
other cached packages' binaries run fine). Following the away precedent
(same PAM-dependent class), the consumer test verifies the packaged
artifacts without executing the daemon:
  1. turnstiled exists, is executable, and is a valid ELF;
  2. pam_turnstile.so exists in lib/security and is a valid ELF;
  3. runtime config (etc/turnstile/turnstiled.conf) and PAM config
     (etc/pam.d/turnstiled) are present;
  4. the dinit backend data is installed under bin/turnstile/dinit
     (upstream installs it under libexecdir/turnstile, but the conan
     MesonToolchain maps libexecdir to bin/, so the packaged path is
     bin/turnstile/dinit — asserted accordingly below).
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <package-folder>", file=sys.stderr)
        return 2
    pkg = sys.argv[1]
    exe = os.path.join(pkg, "bin", "turnstiled")
    pam_mod = os.path.join(pkg, "lib", "security", "pam_turnstile.so")
    conf = os.path.join(pkg, "etc", "turnstile", "turnstiled.conf")
    pam_conf = os.path.join(pkg, "etc", "pam.d", "turnstiled")
    # conan MesonToolchain maps libexecdir to bin/; upstream installs the
    # dinit backend under libexecdir/turnstile → bin/turnstile/dinit here.
    backend = os.path.join(pkg, "bin", "turnstile", "dinit")

    for path in (exe, pam_mod, conf, pam_conf, backend):
        if not os.path.isfile(path):
            raise AssertionError(f"missing packaged file: {path}")
    if not os.access(exe, os.X_OK):
        raise AssertionError(f"turnstiled not executable: {exe}")

    for path in (exe, pam_mod):
        with open(path, "rb") as f:
            if f.read(4) != b"\x7fELF":
                raise AssertionError(f"not an ELF file: {path}")

    print(f"OK: turnstiled present + executable + ELF ({exe})")
    print(f"OK: pam_turnstile.so + configs + dinit backend present under {pkg}")
    print("NOTE: daemon execution requires /run + PAM session; OHOS build"
          " node lacks them and the cached release binary is rejected by"
          " the hmmac exec policy (EPERM) — verified, degraded to static"
          " artifact checks (away precedent)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
