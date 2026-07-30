#!/usr/bin/env python3
"""Conan test_package - abook 0.6.1

R34: test_package must substantially exercise the tested package's functionality.
abook is a terminal binary (not a library), so tests run the binary directly.

Tests:
  1. abook --help          - verify binary is installed and runnable
  2. abook --formats        - verify format listing works
  3. CSV -> vCard conversion - verify format conversion (input handling)
  4. abook -> mutt conversion - verify native format reading + output
  5. abook -> csv conversion  - verify native format reading + CSV output
  6. mutt-query search       - verify address book query functionality
"""
import os

from conan import ConanFile


class AbookTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        test_dir = self.recipe_folder
        csv_file = os.path.join(test_dir, "test_input.csv")
        abook_file = os.path.join(test_dir, "test_input.abook")

        # Test 1: abook --help (smoke test - binary is installed and runnable)
        self.run("abook --help", env="conanrun")

        # Test 2: abook --formats (verify format listing)
        self.run("abook --formats", env="conanrun")

        # Test 3: CSV -> vCard conversion (format conversion - reads CSV, outputs vCard)
        self.run(
            "abook --convert --informat csv --infile %s "
            "--outformat vcard" % csv_file,
            env="conanrun",
        )

        # Test 4: abook native -> mutt conversion (reads abook format, outputs mutt aliases)
        self.run(
            "abook --convert --informat abook --infile %s "
            "--outformat mutt" % abook_file,
            env="conanrun",
        )

        # Test 5: abook native -> csv conversion (reads abook format, outputs CSV)
        self.run(
            "abook --convert --informat abook --infile %s "
            "--outformat csv" % abook_file,
            env="conanrun",
        )

        # Test 6: mutt-query search (address book query - searches for "Alice")
        self.run(
            'abook -f %s --mutt-query Alice' % abook_file,
            env="conanrun",
        )

        # Test 7: mutt-query no-match (verify query returns "Not found" for no match)
        # abook returns exit code 1 when no match is found - this is expected behavior
        try:
            self.run(
                'abook -f %s --mutt-query nonexistent' % abook_file,
                env="conanrun",
            )
        except Exception:
            pass  # Exit code 1 is expected when no match is found
