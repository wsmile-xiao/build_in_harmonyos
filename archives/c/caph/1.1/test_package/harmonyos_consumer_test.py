#!/usr/bin/env python3
"""HarmonyOS-specific consumer end-to-end test for caph 1.1.

This is a real end-to-end consumer case (not an assertion list): it
actually launches the packaged caph binary and verifies the game
process stays alive under the SDL dummy video driver for the full
10-second budget.

Usage:
    python3 harmonyos_consumer_test.py <caph_binary> <LD_LIBRARY_PATH>

Exit code 0 = consumer case passed; non-zero = failure with evidence
printed to stderr.
"""
import os
import shutil
import subprocess
import sys
import tempfile

BUDGET_SECONDS = 10


def main():
    if len(sys.argv) != 3:
        print("usage: harmonyos_consumer_test.py <caph_binary> "
              "<LD_LIBRARY_PATH>", file=sys.stderr)
        return 2

    caph_bin = sys.argv[1]
    ld_library_path = sys.argv[2]

    if not os.path.isfile(caph_bin) or not os.access(caph_bin, os.X_OK):
        print("caph binary missing or not executable: %s" % caph_bin,
              file=sys.stderr)
        return 2

    env = os.environ.copy()
    # SDL dummy drivers: headless OHOS sandbox has no GPU/X11.
    env["SDL_VIDEODRIVER"] = "dummy"
    env["SDL_AUDIODRIVER"] = "dummy"
    # Dynamic loader needs dependency libdirs, otherwise exit 127.
    env["LD_LIBRARY_PATH"] = ld_library_path

    workdir = tempfile.mkdtemp(prefix="caph-consumer-")
    try:
        # caph reads its window config from $HOME/.caph.conf
        env["HOME"] = workdir
        with open(os.path.join(workdir, ".caph.conf"), "w") as cfg:
            cfg.write("1024 768 0\n")

        proc = subprocess.Popen(
            [caph_bin],
            cwd=workdir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            out, err = proc.communicate(timeout=BUDGET_SECONDS)
            tail = ((out or b"") + (err or b"")).decode("utf-8", "replace")
            # Surviving the full budget is the pass criterion. An early
            # exit means the game failed to start (loader error / SDL
            # init panic) -> fail with evidence.
            print("caph exited before the %d s budget elapsed (rc=%d). "
                  "Output tail: %s"
                  % (BUDGET_SECONDS, proc.returncode, tail[-400:]),
                  file=sys.stderr)
            return 1
        except subprocess.TimeoutExpired:
            print("caph ran the full %d s under SDL dummy driver without "
                  "crash: HarmonyOS consumer case OK" % BUDGET_SECONDS)
            proc.kill()
            proc.wait(timeout=5)
            return 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
