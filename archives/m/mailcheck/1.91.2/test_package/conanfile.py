#!/usr/bin/env python3
"""Consumer test package for mailcheck 1.91.2.

mailcheck is a command-line tool (not a library). Upstream 1.91.2 ships NO
test suite — the Makefile defines only all/debug/install/clean targets, with
no check or test target, and there is no tests/ directory, no configure
script, and no CI configuration in the release tarball (see MANIFEST.yml).

This test_package provides a PACKAGE-LEVEL supplementary test: it creates a
real mbox file and .mailcheckrc, runs the mailcheck binary, and verifies
that it correctly reports mail in the mailbox. This is NOT an upstream test.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class MailcheckTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindirs = self.dependencies["mailcheck"].cpp_info.bindirs
        executable = os.path.join(bindirs[0], "mailcheck")
        if not os.path.isfile(executable):
            raise ConanException(f"missing packaged executable: {executable}")

        if not can_run(self):
            self.output.info(
                "cross build: packaged executable exists; runtime checks skipped"
            )
            return

        test_script = os.path.join(self.source_folder, "test_mailcheck.py")
        self.run(
            f'"{sys.executable}" "{test_script}" "{executable}"',
            env="conanrun",
        )
