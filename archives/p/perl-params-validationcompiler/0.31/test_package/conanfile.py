#!/usr/bin/env python3
"""Conan test_package for perl-params-validationcompiler — Perl L1 test.

Tests that the installed Params::ValidationCompiler module can be loaded and used.
Runs test.sh which executes Perl validation tests.

The test attempts a full API test first (validation_for, named params,
default values, return_object mode). If runtime dependencies (Eval::Closure,
Exception::Class) are not installed on the CI worker, it falls back to
verifying that all 3 .pm files are correctly packaged and discoverable
via PERL5LIB.
"""
import os
import glob

from conan import ConanFile
from conan.tools.layout import basic_layout


class PerlparamsvalidationcompilerTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        dep = self.dependencies["perl-params-validationcompiler"]
        pkg_folder = dep.package_folder
        pm_files = glob.glob(
            os.path.join(pkg_folder, "**", "Params", "ValidationCompiler.pm"),
            recursive=True,
        )
        if not pm_files:
            raise Exception("Params/ValidationCompiler.pm not found in package")
        perl_lib_dir = os.path.dirname(os.path.dirname(pm_files[0]))
        # Include system site path for runtime deps (Eval::Closure, etc.)
        deps_lib = os.environ.get("PERL_SITE_LIB", "")
        existing = os.environ.get("PERL5LIB", "")
        parts = [p for p in [perl_lib_dir, deps_lib, existing] if p]
        perl5lib = ":".join(parts)
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'PERL5LIB="{perl5lib}" sh {test_script}')
