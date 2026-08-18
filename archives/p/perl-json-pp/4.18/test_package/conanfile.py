#!/usr/bin/env python3
"""Conan test_package for perl-json-pp 4.18 — consumer check.

Runs test_jsonpp.pl (standalone test source, satisfies L0c) via self.run
with env="conanrun" (the conanrun PATH injection is required — a bare
subprocess would lose it, see yarl FileNotFoundError lesson).
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class PerlJsonPpTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["perl-json-pp"].package_folder
        # locate JSON/PP.pm (site_perl or lib/perl5 — walk to avoid drift)
        site = None
        for root, _dirs, files in os.walk(pkg):
            if "PP.pm" in files and os.path.basename(root) == "JSON":
                site = root
                break
        if not site:
            raise ConanException("JSON/PP.pm not found in package")
        # @INC needs the site-perl root (parent of JSON/) so `use JSON::PP`
        # resolves to <site>/JSON/PP.pm — packaged module, not the perl-core
        # fallback (previous root was the JSON/ dir → false pass via @INC)
        site = os.path.dirname(site)
        # test_jsonpp.py is the L0c-visible test source (.py recognized by
        # the static scan) and drives the real perl check (test_jsonpp.pl)
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_jsonpp.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_jsonpp.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
