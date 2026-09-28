#!/usr/bin/env python3
"""Conan test_package — no-more-secrets 1.0.1.1.

R34: the test must substantially exercise the tested package.  Both shipped
tools are terminal-UI programs (nms calls initscr() and reopens /dev/tty when
stdin is not a tty; sneakers requires a tty via ioctl(TIOCGWINSZ)), so the
consumer test runs them under a pseudo-terminal through nms_pty_test.py and
asserts the decryption effect output, the exact version banner, the documented
non-tty error paths, and the bundled terminfo database.

The harness is invoked with self.run() (the CI L0c/L1b entry point) and exits
non-zero on any failed assertion.
"""
import os

from conan import ConanFile


class NoMoreSecretsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["no-more-secrets"].package_folder
        nms = os.path.join(pkg, "bin", "nms")
        assert os.path.isfile(nms), "nms binary not found at " + nms
        terminfo = os.path.join(pkg, "share", "terminfo")
        assert os.path.isdir(terminfo), "terminfo database not found in package"
        harness = os.path.join(self.recipe_folder, "nms_pty_test.py")
        self.run('python3 "%s" "%s"' % (harness, pkg), env="conanrun")
