#!/usr/bin/env python3
"""Installed-package consumer for vamp-plugin-sdk 2.10.0."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class VampPluginSdkTestConan(ConanFile):
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
        temporary = path + ".vamp-signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", temporary,
             "-selfSign", "1"], check=True, timeout=60
        )
        sections = subprocess.run(
            [readelf, "-SW", temporary], check=True,
            capture_output=True, text=True, timeout=30
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"Signed ELF has invalid .codesign count: {path}")
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)

    def test(self):
        if not can_run(self):
            return
        exe = os.path.join(self.cpp.build.bindirs[0], "vamp_smoke")
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(exe)
        self.run(exe, env="conanrun")
