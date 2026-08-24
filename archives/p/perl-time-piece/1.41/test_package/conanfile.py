#!/usr/bin/env python3
"""Conan test_package for perl-time-piece 1.41 — consumer check.

Runs test_timepiece.pl (standalone test source, satisfies L0c) via
self.run with env="conanrun" (the conanrun PATH injection is required —
a bare subprocess would lose it, see yarl FileNotFoundError lesson).
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class PerlTimePieceTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["perl-time-piece"].package_folder
        # locate Time/Piece.pm (site_perl or lib/perl5 — walk to avoid drift)
        site = None
        for root, _dirs, files in os.walk(pkg):
            if "Piece.pm" in files and os.path.basename(root) == "Time":
                # @INC needs the site-perl root (parent of Time/) so
                # `use Time::Piece` resolves to <site>/Time/Piece.pm
                site = os.path.dirname(root)
                break
        if not site:
            raise ConanException("Time/Piece.pm not found in package")
        # test_timepiece.py is the L0c-visible test source (.py recognized
        # by the static scan) and drives the real perl check (.pl)
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_timepiece.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_timepiece.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
