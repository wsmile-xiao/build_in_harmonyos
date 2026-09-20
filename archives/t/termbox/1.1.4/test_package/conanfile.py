#!/usr/bin/env python3
"""Consumer tests for termbox 1.1.4."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class TermboxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bindir = self.cpp.build.bindir
            executables = [
                os.path.join(bindir, "test_api"),
                os.path.join(bindir, "test_ohos_pty"),
            ]
            if str(self.settings.os) == "OHOS":
                for executable in executables:
                    self._sign_ohos_elf(executable)
            for executable in executables:
                self.run(executable, env="conanrun")
        else:
            self.output.warning(
                "Cross-built tests require execution on a HarmonyOS device"
            )

    @staticmethod
    def _sign_ohos_elf(path):
        if not os.path.isfile(path):
            raise ConanException(f"Missing OHOS test executable: {path}")
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        objcopy = shutil.which("llvm-objcopy") or (
            "/data/service/hnp/bin/llvm-objcopy"
        )
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
