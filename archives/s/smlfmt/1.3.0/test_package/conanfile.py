#!/usr/bin/env python3
"""Consumer and negative tests for packaged smlfmt."""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class SmlfmtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.info("交叉构建场景不运行目标程序")
            return
        package = self.dependencies["smlfmt"].package_folder
        smlfmt = os.path.join(package, "bin", "smlfmt")
        if not os.path.isfile(smlfmt):
            raise ConanException("package validation missing smlfmt binary")
        self.output.info("PACKAGE_VALIDATION_MARKER: smlfmt binary present PASS")

        # Positive consumer test: well-formatted SML must be accepted
        good = os.path.join(self.source_folder, "good.sml")
        self.run(f'"{smlfmt}" --preview-only --safety-check "{good}"',
                 env="conanrun")
        self.output.info("CONSUMER_TEST_MARKER: parse good.sml PASS")

        # Negative test: invalid SML must be rejected (non-zero exit).
        # Per project convention use self.run(check=False) and inspect return code
        # rather than subprocess.run or delegating to a wrapper script.
        bad = os.path.join(self.source_folder, "bad.sml")
        ret = self.run(f'"{smlfmt}" --preview-only --safety-check "{bad}"',
                       env="conanrun", ignore_errors=True)
        if ret == 0:
            raise ConanException("NEGATIVE_TEST failed: bad.sml should be rejected")
        self.output.info("NEGATIVE_TEST_MARKER: bad.sml rejected PASS")

        # Format check test: unformatted file must be detected (non-zero exit)
        unformatted = os.path.join(self.source_folder, "unformatted.sml")
        ret = self.run(f'"{smlfmt}" --check "{unformatted}"',
                       env="conanrun", ignore_errors=True)
        if ret == 0:
            raise ConanException("FORMAT_CHECK_TEST failed: unformatted.sml should be detected")
        self.output.info("FORMAT_CHECK_TEST_MARKER: unformatted.sml detected PASS")
