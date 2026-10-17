#!/usr/bin/env python3
"""Consumer test for qtpositioning on HarmonyOS PC."""

import os
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QtpositioningTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        qtbase_pkg = self.dependencies["qtbase"].package_folder
        pkg = self.dependencies["qtpositioning"].package_folder
        # Qt6Config lives in the qtbase package; Qt6PositioningConfig lives in
        # the qtpositioning package. Qt only searches the additional prefixes
        # listed in QT_ADDITIONAL_PACKAGES_PREFIX_PATH for module configs.
        tc.cache_variables["CMAKE_PREFIX_PATH"] = qtbase_pkg
        tc.cache_variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = pkg
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self) and str(self.settings.os) == "OHOS":
            for binary in self._test_binaries():
                self._sign(binary)

    def _test_binaries(self):
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanInvalidConfiguration(
                "qtpositioning test package has no build bindir"
            )
        return [os.path.join(bindirs[0], "test_qtpositioning")]

    def _sign(self, path):
        """Self-sign the test binary so the OHOS loader permits execution."""
        original_mode = stat.S_IMODE(os.stat(path).st_mode)
        signer = shutil.which("binary-sign-tool")
        if not signer:
            raise ConanInvalidConfiguration(
                "binary-sign-tool not found; it is required to run OHOS ELF binaries"
            )
        with tempfile.TemporaryDirectory(
            prefix=".conan-sign-", dir=os.path.dirname(path)
        ) as temp_dir:
            unsigned = os.path.join(temp_dir, "unsigned")
            signed = os.path.join(temp_dir, "signed")
            shutil.copy2(path, unsigned)
            subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    unsigned,
                    "-outFile",
                    signed,
                    "-selfSign",
                    "1",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            os.replace(signed, path)
            os.chmod(path, original_mode)

    def test(self):
        if not can_run(self):
            self.output.info("Skipping execution: cross-build without an emulator")
            return

        executable = os.path.join(self.cpp.build.bindirs[0], "test_qtpositioning")
        self.run(executable, env="conanrun", ignore_errors=False)
