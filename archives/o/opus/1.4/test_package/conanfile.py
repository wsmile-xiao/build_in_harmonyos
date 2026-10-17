#!/usr/bin/env python3
"""Installed-package consumer for Opus 1.4."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class OpusTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        output = path + ".opus-signed"
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", output,
                        "-selfSign", "1"], check=True, timeout=60)
        sections = subprocess.run([readelf, "-SW", output], check=True,
                                  capture_output=True, text=True, timeout=30).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("Signed consumer has invalid .codesign count")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o555)
        os.replace(output, path)

    def test(self):
        if can_run(self):
            executable = os.path.join(self.cpp.build.bindir, "opus_consumer")
            if str(self.settings.os) == "OHOS":
                self._sign_ohos_elf(executable)
            self.run(f'"{executable}"', env="conanrun")
