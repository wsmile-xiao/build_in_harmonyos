#!/usr/bin/env python3
"""Installed-package consumer test for cubature 1.0.4."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class CubatureTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        toolchain.variables["CUBATURE_TEST_OHOS"] = str(self.settings.os) == "OHOS"
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            executables = ["test_cubature"]
            if str(self.settings.os) == "OHOS":
                executables.append("test_cubature_ohos")
            for name in executables:
                executable = os.path.join(self.cpp.build.bindir, name)
                if str(self.settings.os) == "OHOS":
                    self._sign_ohos_elf(executable)
                self.run(f'"{executable}"', env="conanrun")
        else:
            self.output.warning("Target consumer test is not runnable in this build context")

    @staticmethod
    def _sign_ohos_elf(path):
        if not os.path.isfile(path):
            raise ConanException(f"Missing OHOS consumer executable: {path}")
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer) or not os.path.isfile(objcopy):
            raise ConanException("Required OHOS signing tools are missing")
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            check=True,
            timeout=30,
        )
        subprocess.run(
            [
                signer,
                "sign",
                "-inFile",
                path,
                "-outFile",
                path,
                "-selfSign",
                "1",
            ],
            check=True,
            timeout=60,
        )
        os.chmod(path, (os.stat(path).st_mode & 0o777) | 0o055)
