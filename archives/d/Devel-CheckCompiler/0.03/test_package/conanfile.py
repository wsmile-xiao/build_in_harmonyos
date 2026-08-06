#!/usr/bin/env python3
"""Conan test_package — Devel-CheckCompiler 0.03

L1 test: Verify that Devel::CheckCompiler module is installed correctly
and its core API (check_compile, check_c99) can be called.

check_c99() may return false on OHOS due to -fstack-protector-strong
incompatibility with ld.lld — this is a known platform limitation,
not a packaging failure. The test verifies module loading and API
availability, not C99 detection success.
"""
import os
import glob

from conan import ConanFile


class DevelCheckCompilerTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find Devel/CheckCompiler.pm in the package folder
        pkg = self.dependencies["devel-checkcompiler"]
        pkg_folder = pkg.package_folder
        pm_files = glob.glob(
            os.path.join(pkg_folder, "**", "CheckCompiler.pm"),
            recursive=True
        )
        if not pm_files:
            raise Exception("Devel/CheckCompiler.pm not found in package")
        # lib_dir = the directory containing 'Devel' (i.e., .../lib/perl5)
        # CheckCompiler.pm is at .../lib/perl5/Devel/CheckCompiler.pm
        # so we need 2 levels up from the .pm file to get .../lib/perl5
        lib_dir = os.path.dirname(os.path.dirname(pm_files[0]))

        # Use the static test script (test_checkcompiler.sh)
        test_script = os.path.join(os.path.dirname(__file__), "test_checkcompiler.sh")
        self.run(f'sh "{test_script}" "{lib_dir}"', env="conanrun")
