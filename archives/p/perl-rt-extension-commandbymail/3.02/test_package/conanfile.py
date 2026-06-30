#!/usr/bin/env python3
"""Conan test_package for perl-rt-extension-commandbymail 3.02.

RT::Extension::CommandByMail is a pure-Perl RT4 extension.  The module
requires RT to be fully functional at runtime, so the smoke test verifies
that the .pm files are installed at the expected PERL5LIB path and that
perl can locate the file (even though `use` will fail without RT installed).
"""
import os
import subprocess

from conan import ConanFile


class PerlRtExtensionCommandByMailTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get package folder from dependency
        dep = self.dependencies["perl-rt-extension-commandbymail"]
        pkg_lib = os.path.join(dep.package_folder, "lib", "perl5")

        expected_files = [
            "RT/Extension/CommandByMail.pm",
            "RT/Extension/CommandByMail/Test.pm",
            "RT/Interface/Email/Action/CommandByMail.pm",
            "RT/Interface/Email/Filter/TakeAction.pm",
        ]
        for rel in expected_files:
            full = os.path.join(pkg_lib, rel)
            assert os.path.isfile(full), f"Missing installed file: {full}"
        self.output.info(f"All {len(expected_files)} .pm files verified in {pkg_lib}")

        # Try perl -M to confirm file is locatable (will fail on `use` due to RT
        # not being installed, but confirms the file path is correct)
        env = os.environ.copy()
        env["PERL5LIB"] = pkg_lib
        result = subprocess.run(
            ["perl", "-e", "use RT::Extension::CommandByMail;"],
            capture_output=True, text=True, env=env
        )
        # Expected: module file found but RT::EmailParser dependency missing
        if "Can't locate RT/EmailParser.pm" in result.stderr or "Can't locate RT.pm" in result.stderr:
            self.output.info("Module file located successfully (RT runtime dependency expected to be missing)")
        elif result.returncode == 0:
            self.output.info("Module loaded successfully")
        else:
            self.output.warn(f"perl -M returned {result.returncode}: {result.stderr[:200]}")
