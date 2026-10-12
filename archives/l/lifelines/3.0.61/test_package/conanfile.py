#!/usr/bin/env python3
"""Conan test_package for lifelines 3.0.61.

Exercises the installed ``llines`` / ``llexec`` binaries as a consumer would:
build a Lifelines database from the upstream GEDCOM fixture, run two
consumer-written report programs through ``llexec``, check the genealogical
content of both reports, and check three negative paths.
"""
import os

from conan import ConanFile


class LifelinesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        work = os.path.join(self.build_folder, "consumer-work")
        os.makedirs(work, exist_ok=True)
        script = os.path.join(self.recipe_folder, "check_lifelines.py")
        # /tmp is read-only on HarmonyOS devices, so the suite runs against a
        # private TMPDIR (honoured by patch 0001).  TERM=xterm is the entry the
        # package ships under share/terminfo and exports via TERMINFO_DIRS.
        self.run(f'TMPDIR="{work}" TERM=xterm python3 "{script}" "{work}"',
                 env="conanrun")
