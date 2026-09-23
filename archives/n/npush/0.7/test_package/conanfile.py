#!/usr/bin/env python3
"""Conan test_package — npush 0.7.

npush is a full-screen ncurses game, so a plain `npush --version` style
smoke test is not possible (it ignores argv and needs a terminal).  We
therefore run a real *functional* check: spawn the packaged `npush`
launcher inside a pseudo-terminal, wait until the "Welcome to nPush" menu
is rendered, send "Down Down Enter" to select the Quit entry and require a
clean exit code 0.  This genuinely exercises the packaged binary, its
ncurses dependency (initscr / terminfo from the ncurses conan package) and
input handling.
"""
import os
import sys

from conan import ConanFile


class NpushTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # ncurses is a (transitive) runtime dependency of npush; requiring it
        # directly here makes its runenv (TERMINFO -> share/terminfo) part of
        # the "conanrun" environment used by the functional test below.
        self.requires("ncurses/6.4")

    def test(self):
        pkg = self.dependencies["npush"].package_folder
        bin_path = os.path.join(pkg, "bin", "npush")
        self.output.info(f"Checking npush launcher exists: {bin_path}")
        if not os.path.exists(bin_path):
            raise Exception(f"npush launcher not found: {bin_path}")

        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "functional_test.py")
        # env="conanrun" brings in the ncurses TERMINFO run-environment.
        # We use sys.executable (the conan interpreter) to avoid depending on
        # python3 being present on the target PATH.
        self.run(f'"{sys.executable}" "{script}" "{bin_path}"', env="conanrun")
