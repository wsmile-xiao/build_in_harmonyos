#!/usr/bin/env python3
"""Conan test_package — mtm 1.2.1.

mtm is a full-screen ncurses terminal multiplexer with no --help/--version
flag (USAGE: mtm [-T NAME] [-t NAME] [-c KEY]).  A plain argv smoke test is
therefore not meaningful; we run a functional check: spawn the packaged
`mtm` inside a pseudo terminal, wait until it multiplexes its hosted
shell's output to the pty (proving forkpty + initscr + terminfo all work),
then delete the last node via the command key (Ctrl-g w), which makes mtm
quit cleanly, and require exit 0.
"""
import os
import sys

from conan import ConanFile


class MtmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # ncurses is the runtime dependency of mtm; requiring it directly
        # makes its runenv (TERMINFO -> share/terminfo with the `screen`
        # entry) part of the "conanrun" environment for the test below.
        self.requires("ncurses/6.6")

    def test(self):
        pkg = self.dependencies["mtm"].package_folder
        bin_path = os.path.join(pkg, "bin", "mtm")
        self.output.info(f"Checking mtm binary exists: {bin_path}")
        if not os.path.exists(bin_path):
            raise Exception(f"mtm binary not found: {bin_path}")

        testdir = os.path.dirname(os.path.abspath(__file__))
        # env="conanrun" brings in the ncurses TERMINFO run-environment,
        # required by the PTY-based tests (initscr needs the `screen` entry).
        #
        # Consumer functional test (1/1): multiplexer behaviour in a pty
        # (4 assertions a1-a4, listed in MANIFEST.yml).
        functional = os.path.join(testdir, "functional_test.py")
        self.run(f'"{sys.executable}" "{functional}" "{bin_path}"',
                 env="conanrun")

        # OHOS-specific platform contract test (1/1): AArch64 ELF, musl
        # interpreter, .codesign section, no libutil in NEEDED, forkpty
        # resolved by OHOS libc, real PTY run (6 assertions o1-o6).
        ohos = os.path.join(testdir, "ohos_specific_test.py")
        self.run(f'"{sys.executable}" "{ohos}" "{bin_path}"', env="conanrun")
