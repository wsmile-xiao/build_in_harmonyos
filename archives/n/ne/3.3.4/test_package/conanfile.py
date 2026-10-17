#!/usr/bin/env python3
"""Conan test_package - ne 3.3.4

R34: test_package must substantially exercise the tested package.
ne is an interactive terminal editor. Its non-tty code path aborts
(ne.c: freopen("/dev/tty") fails -> abort), so tests run the binary
under a pseudo-terminal via ne_pty_test.py, which is invoked with
self.run() (CI L0c口径).

Tests (all under pty, TERM=ansi, TERMINFO pointing at the ne package's
shipped terminfo database; ne has no --version flag -- --help prints the
version banner):
  1. --help smoke test (version banner + option list)
  2. macro mode: InsertString + Save + Exit on a temp file, verifying
     the edit was persisted to disk (real editor functionality)
  3. macro mode: Find + ReplaceAll + Save, verifying search/replace
  4. macro mode: insert + Undo + Save, verifying undo restores the
     original content (core invariant of upstream test.rc)
"""
import os

from conan import ConanFile


class NeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        ne_pkg = self.dependencies["ne"].package_folder
        ne_bin = os.path.join(ne_pkg, "bin", "ne")
        assert os.path.isfile(ne_bin), "ne binary not found at " + ne_bin
        terminfo = os.path.join(ne_pkg, "share", "terminfo")
        assert os.path.isdir(terminfo), "terminfo database not found in package"
        harness = os.path.join(self.recipe_folder, "ne_pty_test.py")
        # ne needs a tty (aborts otherwise) - the harness runs it under a
        # pty with TERMINFO pointing at the shipped terminfo database.
        self.run(
            'python3 "%s" "%s" "%s"' % (harness, ne_bin, terminfo),
            env="conanrun",
        )
