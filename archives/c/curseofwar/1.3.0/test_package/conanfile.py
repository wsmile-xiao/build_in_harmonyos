#!/usr/bin/env python3
"""Conan test_package — curseofwar 1.3.0.

curseofwar is a terminal game, so the L1 test runs the real binary (R34):
- `curseofwar -v` prints exactly "1.3.0"
- `curseofwar -h` prints the help screen (game title + arguments section)
- a headless 6-second run with a fixed map seed proves the full game
  initialization path (map generation, player placement) and the real-time
  main loop (kings_move + simulate ticks advance the in-game date), with a
  clean endwin terminal restoration on SIGTERM.
"""
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException


class CurseofwarTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        # The absolute HNP path is missing on some preflight workers, so
        # resolve via PATH before falling back to the hard-coded path.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"

        dep = self.dependencies["curseofwar"]
        game = os.path.join(dep.package_folder, "bin", "curseofwar")
        if not os.path.isfile(game):
            raise ConanException("packaged curseofwar binary not found at {}".format(game))

        # ncurses ships its terminfo database inside its package folder
        # (share/terminfo) and exports TERMINFO/TERMINFO_DIRS through its
        # runenv_info. On CI workers the aggregated conanrun.sh is not
        # always sourced for the test() step (observed: TERMINFO unset on
        # worker CI-037), so resolve the terminfo path explicitly and pass
        # a merged environment to test.sh — the headless game-loop smoke
        # always finds a terminfo entry for TERM=xterm this way.
        # Resolution order:
        #   1. the VirtualRunEnv-generated conanrun*.sh scripts (they carry
        #      the ncurses runenv_info exports — TERMINFO=...)
        #   2. the dependency-graph package folders (direct or transitive)
        terminfo = None

        # 1. parse the generated conanrun scripts (generators_folder ==
        #    the test_package folder itself for explicit test packages)
        generators_dir = self.generators_folder
        for fname in sorted(os.listdir(generators_dir)) if os.path.isdir(generators_dir) else []:
            if not (fname.startswith("conanrunenv") and fname.endswith(".sh")):
                continue
            try:
                with open(os.path.join(generators_dir, fname), "r", errors="replace") as fh:
                    for line in fh:
                        line = line.strip()
                        if line.startswith("export TERMINFO="):
                            cand = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if cand and os.path.isdir(cand):
                                terminfo = cand
                                break
            except OSError:
                pass
            if terminfo:
                break

        # 2. dependency graph fallback
        if not terminfo:
            try:
                ncurses_dep = self.dependencies["ncurses"]
                pf = ncurses_dep.package_folder
                if pf:
                    cand = os.path.join(pf, "share", "terminfo")
                    if os.path.isdir(cand):
                        terminfo = cand
            except KeyError:
                for ref, req in self.dependencies.items():
                    if "ncurses" not in str(ref):
                        continue
                    if req.package_folder:
                        cand = os.path.join(req.package_folder, "share", "terminfo")
                        if os.path.isdir(cand):
                            terminfo = cand
                            break

        if terminfo:
            os.environ.setdefault("TERMINFO", terminfo)
            os.environ.setdefault("TERMINFO_DIRS", terminfo)

        # test.sh runs 3 real assertions against the packaged binary:
        #   1. `curseofwar -v` prints exactly "1.3.0"
        #   2. `curseofwar -h` contains "Command line arguments" + title
        #   3. headless game-loop smoke: map generated + in-game date
        #      advanced + endwin terminal restoration
        script = os.path.join(self.source_folder, "test.sh")
        discovered = 3
        passed = 0
        try:
            self.run(
                '{bash} "{script}" "{game}"'.format(bash=bash, script=script, game=game),
            )
            passed = discovered
        except Exception as exc:
            self.output.error("test.sh failed: {}".format(exc))

        # HMBS machine-evidence markers, printed on the Conan output stream
        # (same channel as dhex 0.69 / lzop 1.04, which passed the gate).
        # test_package count = the 3 real binary assertions.
        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": '{bash} test.sh'.format(bash=bash),
            "discovered": discovered,
            "passedCount": passed,
        }
        print("HMBS_TEST_PACKAGE_RESULT={}".format(json.dumps(tp_result)))

        # Upstream curseofwar 1.3.0 has no test suite (audited tarball,
        # see test_package/MANIFEST.yml upstream_tests_exist: false): the
        # hand-written Makefile defines no check/test target, so the
        # honest result is no_tests/0.
        ut_result = {
            "status": "no_tests",
            "framework": "makefile",
            "command": "make check",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "curseofwar-1.3.0.tar.gz audited (sha256 "
                "2a90204d95a9f29a0e5923f43e65188209dc8be9d9eb93576404e3f79b8a652b): "
                "no tests/ directory and no test source files anywhere in the "
                "tree; the hand-written Makefile defines only all/clean/uninstall/install "
                "targets with no check/test target; upstream ships no unit test "
                "harness (game project, interactive ncurses RTS), so make check "
                "executes zero test cases"
            ),
        }
        print("HMBS_UPSTREAM_TEST_RESULT={}".format(json.dumps(ut_result)))

        if passed != discovered:
            raise ConanException(
                "curseofwar test_package assertions failed: {}/{}".format(passed, discovered)
            )
