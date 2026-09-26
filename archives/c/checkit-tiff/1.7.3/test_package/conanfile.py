#!/usr/bin/env python3
"""Conan test_package for checkit-tiff — runs the 7 E2E scenarios in test.sh
when the target can actually run. Cross-compiled OHOS binaries cannot run
on a Windows build host, so test() is skipped there (and says so)."""
import os
import subprocess

from conan import ConanFile
from conan.tools.build import can_run


class CheckitTiffTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Target binaries cannot run in this configuration")
            return
        # Run the E2E test script (test.sh) which exercises 7 scenarios:
        # 1) valid baseline passes, 2) missing mandatory tag 270 rejected,
        # 3) valid PCRE2 regex grammar accepted, 4) missing tag 9999 rejected,
        # 5) PCRE2 negative match rejected, 6) invalid regex rejected,
        # 7) control: valid grammar still accepted
        test_script = os.path.join(self.source_folder, "test.sh")
        if not os.path.isfile(test_script):
            raise FileNotFoundError(f"test.sh not found at {test_script}")
        # Make sure it's executable
        os.chmod(test_script, 0o755)
        # Set env vars for test.sh to find installed package files
        pkg = self.dependencies["checkit-tiff"]
        os.environ["CONAN_PACKAGE_FOLDER"] = pkg.package_folder
        self.run(f"bash {test_script}", env="conanrun")