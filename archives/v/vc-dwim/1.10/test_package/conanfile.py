#!/usr/bin/env python3
"""Conan test_package for vc-dwim 1.10 — runs the R34 consumer check.

Executes the packaged scripts through test_vc_dwim.py (VirtualRunEnv provides
PERL5LIB from perl-pod-parser and ctags on PATH):
  1. smoke: vc-dwim / vc-chlog --version
  2. functional: vc-dwim --diff on a real git worktree — ChangeLog entry must
     match the working-tree diff (perl interpreter + VC.pm + git plumbing)
  3. functional: vc-chlog --stdin generates a GCS ChangeLog entry from a
     unified diff (awk/patch pipeline)
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            raise ConanException("cannot run on this platform")
        pkg = self.dependencies["vc-dwim"].package_folder
        bindir = os.path.join(pkg, "bin")
        for script in ("vc-dwim", "vc-chlog"):
            if not os.path.isfile(os.path.join(bindir, script)):
                raise ConanException(f"{script} missing under {bindir}")
        for pm in ("VC.pm", "Coda.pm", "ProcessStatus.pm"):
            if not os.path.isfile(os.path.join(pkg, "share", "vc-dwim", pm)):
                raise ConanException(f"{pm} missing under {pkg}/share/vc-dwim")
        test_script = os.path.join(os.path.dirname(__file__), "test_vc_dwim.py")
        self.run(f'{sys.executable} "{test_script}" "{bindir}"', env="conanrun")
