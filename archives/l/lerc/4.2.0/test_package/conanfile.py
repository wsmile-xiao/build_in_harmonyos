#!/usr/bin/env python3
"""Installed-package API tests for lerc 4.2.0."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


TEST_EXECUTABLES = (
    "lerc_api_surface",
    "lerc_version_contract",
    "lerc_upstream_test",
)


class LercTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c", "upstream_test/**"

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
            raise ConanException("lerc target consumers are not runnable")
        # 上游 LercTest main() 在无 LERCTEST_NONINTERACTIVE 时会走
        # `getchar()` 等待回车（CI 无 stdin → 阻塞至 4h 超时）。CI 必须非交互。
        os.environ.setdefault("LERCTEST_NONINTERACTIVE", "1")
        for name in TEST_EXECUTABLES:
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
