#!/usr/bin/env python3
"""Installed-package API tests for libXext 1.3.7."""

import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


TEST_EXECUTABLES = ("libxext_sync_value_contract", "libxext_registry_contract")


class LibxextTestConan(ConanFile):
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
            raise ConanException("libxext target consumers are not runnable")
        runtime_dir = None
        try:
            if str(self.settings.os) == "OHOS":
                runtime_dir = tempfile.mkdtemp(
                    prefix="libxext-test-", dir="/data/storage/el2/base/cache"
                )
            for name in TEST_EXECUTABLES:
                executable = os.path.join(self.cpp.build.bindir, name)
                if runtime_dir is not None:
                    staged = os.path.join(runtime_dir, name)
                    shutil.copy2(executable, staged)
                    self._sign_ohos_elf(staged)
                    executable = staged
                self.run(f'"{executable}"', env="conanrun")
        finally:
            if runtime_dir is not None:
                shutil.rmtree(runtime_dir)

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
