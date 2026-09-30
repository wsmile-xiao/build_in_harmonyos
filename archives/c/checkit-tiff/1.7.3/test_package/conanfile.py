#!/usr/bin/env python3
"""Conan test_package for checkit-tiff — runs the 7 E2E scenarios in test.sh.
This test must always run (even when can_run returns False) to satisfy
the L1e destructive negative test which verifies the test genuinely
depends on the package artifacts."""
import os

from conan import ConanFile


class CheckitTiffTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Run the E2E test script (test.sh) which exercises 7 scenarios:
        # 1) valid baseline passes, 2) missing mandatory tag 270 rejected,
        # 3) valid PCRE2 regex grammar accepted, 4) missing tag 9999 rejected,
        # 5) PCRE2 negative match rejected, 6) invalid regex rejected,
        # 7) control: valid grammar still accepted
        # NOTE: We do NOT skip on can_run() because the CI L1e destructive test
        # requires the test to run and fail when package artifacts are removed.
        test_script = os.path.join(self.source_folder, "test.sh")
        if not os.path.isfile(test_script):
            raise FileNotFoundError(f"test.sh not found at {test_script}")
        # Make sure it's executable
        os.chmod(test_script, 0o755)
        # Set env vars for test.sh to find installed package files
        pkg = self.dependencies["checkit-tiff"]
        os.environ["CONAN_PACKAGE_FOLDER"] = pkg.package_folder
        self.run(f"bash {test_script}", env="conanrun")