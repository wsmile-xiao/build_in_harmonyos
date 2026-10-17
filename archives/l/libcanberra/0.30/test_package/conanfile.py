#!/usr/bin/env python3
"""Installed-package API tests for libcanberra 0.30.

libcanberra ships no automated test suite upstream (the only executable,
test-canberra, is a noinst demo that plays hard-coded system sound files
through a real audio backend and has no assertions).  The two consumers here
link the published libcanberra/0.30 and drive the public canberra.h API on
the built-in null driver, which needs no audio device:
  * libcanberra_api_surface     strong-typed relocation of every exported
                                ca_proplist_* / ca_context_* / ca_strerror
                                symbol plus an error-string sweep.
  * libcanberra_version_contract  CA_MAJOR/CA_MINOR/CA_CHECK_VERSION contract,
                                error-code enumeration checks, and a full
                                create/open/play/callback/playing/cancel/
                                destroy lifecycle on the null driver.
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibcanberraTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c"

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

    def test(self):
        if not can_run(self):
            raise ConanException("libcanberra target consumers are not runnable")
        for name in ("libcanberra_api_surface", "libcanberra_version_contract"):
            executable = os.path.join(self.cpp.build.bindir, name)
            if str(self.settings.os) == "OHOS":
                self._sign_ohos_elf(executable)
            self.run(f'"{executable}"', env="conanrun")

    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        readelf = shutil.which("llvm-readelf") or (
            "/data/service/hnp/bin/llvm-readelf"
        )
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        temporary = f"{path}.signed"
        subprocess.run(
            [
                signer,
                "sign",
                "-inFile",
                path,
                "-outFile",
                temporary,
                "-selfSign",
                "1",
            ],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", temporary],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"signed consumer has invalid .codesign: {path}")
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)
