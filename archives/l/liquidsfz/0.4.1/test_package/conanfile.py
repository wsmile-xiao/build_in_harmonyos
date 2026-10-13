#!/usr/bin/env python3
"""Build and run a liquidsfz consumer that renders audio from an SFZ file."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LiquidsfzTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        names = ["test_liquidsfz"]
        if str(self.settings.os) == "OHOS":
            names.append("test_liquidsfz_ohos")
        for name in names:
            executable = os.path.join(self.cpp.build.bindir, name)
            if str(self.settings.os) == "OHOS":
                self._sign_test(executable)
            self.run(executable, cwd=self.build_folder, env="conanrun")

    @staticmethod
    def _sign_test(executable):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        signed = executable + ".signed"
        subprocess.run([signer, "sign", "-inFile", executable,
                        "-outFile", signed, "-selfSign", "1"], check=True)
        sections = subprocess.run([readelf, "-SW", signed], check=True,
                                  capture_output=True, text=True).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("Invalid consumer test signature")
        os.chmod(signed, (os.stat(executable).st_mode & 0o777) | 0o055)
        os.replace(signed, executable)
        os.chmod(executable, 0o755)
