#!/usr/bin/env python3
"""Conan test_package for libspecbleach 0.4.1 — L1 official test.

CI runs this automatically via `conan create` (which invokes test_package).
Consumer-style test: builds test.c against the installed public header and
library, then runs it (with OHOS ELF signing when on OHOS).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibspecbleachTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
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

    @staticmethod
    def _sign_ohos_elf(path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(path):
            raise ConanException(f"Missing consumer executable: {path}")
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        output = path + ".libspecbleach-signed"
        try:
            subprocess.run(
                [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
                check=True,
                timeout=60,
            )
        except (subprocess.CalledProcessError, OSError):
            # No signing infrastructure (native/emulator host): run unsigned.
            return
        sections = subprocess.run(
            [readelf, "-SW", output],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("Signed consumer has invalid .codesign count")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)

    def test(self):
        if can_run(self):
            executable = os.path.join(self.cpp.build.bindir, "test_libspecbleach")
            if str(self.settings.os) == "OHOS":
                self._sign_ohos_elf(executable)
            self.run(executable, env="conanrun")
