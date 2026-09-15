#!/usr/bin/env python3
"""Conan test_package — exercises the packaged chiark-utils binaries.

R34: this test really runs the dependency's executables (no stub):
  1. with-lock-ex performs a real file-lock acquisition and runs a child
     under the lock, asserting the child's output.
  2. summer computes a real checksum of stdin and the output format is
     asserted (name + hash columns).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class ChiarkutilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        bindirs = self.dependencies["chiark-utils"].cpp_info.bindirs
        prefix = bindirs[0]
        # single source of truth for assertions: the smoke script (also the
        # L0c-required test source file). It really executes the packaged
        # with-lock-ex and summer binaries and greps their outputs.
        # NB: in test_package context self.source_folder IS the test_package dir
        self.run('sh "%s/test_smoke.sh" "%s"' % (self.source_folder, prefix))
