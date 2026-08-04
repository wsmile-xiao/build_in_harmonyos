#!/usr/bin/env python3
"""Conan test_package for gel 0.3.0 — Ruby script test.

Verifies that gel is properly packaged and can at least display help.
Since gel requires Ruby runtime, the test checks:
1. The gel executable exists in bin/
2. The lib/ directory structure is intact
3. If Ruby is available, runs gel --help and verifies output
"""
import os
import shutil

from conan import ConanFile


class GelTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["gel"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        lib_dir = os.path.join(dep.package_folder, "lib")

        # Test 1: Verify gel executable exists
        gel_bin = os.path.join(bin_dir, "gel")
        assert os.path.isfile(gel_bin), f"gel executable not found at {gel_bin}"
        print(f"Test 1 PASSED: gel executable found at {gel_bin}")

        # Test 2: Verify lib/gel/ directory exists
        gel_lib = os.path.join(lib_dir, "gel")
        assert os.path.isdir(gel_lib), f"lib/gel/ directory not found at {gel_lib}"
        print(f"Test 2 PASSED: lib/gel/ directory found at {gel_lib}")

        # Test 3: Verify lib/gel/version.rb exists
        version_rb = os.path.join(gel_lib, "version.rb")
        assert os.path.isfile(version_rb), f"lib/gel/version.rb not found at {version_rb}"
        print(f"Test 3 PASSED: lib/gel/version.rb found")

        # Test 4: If Ruby is available, run gel --help
        ruby = shutil.which("ruby")
        if ruby:
            print(f"Ruby found at {ruby}, running gel --help...")
            self.run(
                f'cd "{self.source_folder}" && '
                f'bash test.sh "{bin_dir}" "{lib_dir}"',
                env="conanrun"
            )
        else:
            print("Ruby not available — skipping runtime test (structural tests passed)")
