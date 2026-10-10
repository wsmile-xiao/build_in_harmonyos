#!/usr/bin/env python3
"""Conan test_package — qodem 1.0.1

R34: run the installed binary for real, not a stub.  qodem is a terminal
emulator, so the checks cover the three layers this package is built on:

  1. argument/banner handling — no curses involved (`--version`, `--help`)
  2. option table + filesystem — `--create-config` writes a full options file
  3. a real terminal session — `forkpty()` child shell + wide-char ncurses
     render, asserted on the capture file written by `--capfile`

Environment notes (details in ../notes.md §6):
  * conan's VirtualRunEnv forces `TERM=dumb`, which a curses program cannot
    use; test.sh upgrades it to `xterm`.
  * terminfo lives in the ncurses dependency package; its runenv is not
    propagated transitively, so the path is handed to test.sh explicitly.
  * output goes to `build/` (gitignored) so a test run never dirties the
    recipe directory.
"""
import os

from conan import ConanFile


class QodemTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Required directly as well: in the test graph conan skips the binary
        # of transitive dependencies, so without this `self.dependencies`
        # would expose no package_folder and no runenv for ncurses (where
        # terminfo lives).
        self.requires("ncurses/6.6")

    def test(self):
        out_dir = os.path.join(self.build_folder, "build", "qodem-test-out")
        os.makedirs(out_dir, exist_ok=True)
        terminfo = ""
        ncurses = self.dependencies.get("ncurses")
        if ncurses is not None and ncurses.package_folder:
            terminfo = os.path.join(ncurses.package_folder, "share", "terminfo")
        # /system/bin/sh (mksh) cannot exec the installed ELF; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("{} test.sh {} {}".format(bash, out_dir, terminfo), env="conanrun")
