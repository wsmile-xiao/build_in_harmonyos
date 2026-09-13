#!/usr/bin/env python3
"""Conan test_package — datefudge 1.27 functional and HarmonyOS checks."""

import os
import platform
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class DatefudgeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["DATEFUDGE_EXPECT_OHOS"] = (
            str(self.settings.os) == "OHOS"
        )
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if str(self.settings.os) == "OHOS":
            self._verify_ohos_artifacts()
            self._sign_ohos_executable()

    def test(self):
        package_folder = self.dependencies["datefudge"].package_folder
        executable = os.path.join(self.cpp.build.bindirs[0], "test_datefudge")
        script = os.path.join(self.source_folder, "test.sh")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        target_is_arm64 = str(self.settings.arch) == "armv8"
        machine_is_arm64 = platform.machine().lower() in ("aarch64", "arm64")
        runtime_available = can_run(self) and (
            not target_is_arm64 or machine_is_arm64
        )
        mode = "run" if runtime_available else "inspect"
        self.run(
            f'"{bash}" "{script}" "{package_folder}" "{executable}" "{mode}"',
            env="conanrun",
        )

    def _verify_ohos_artifacts(self):
        package_folder = self.dependencies["datefudge"].package_folder
        library = os.path.join(package_folder, "lib", "datefudge", "datefudge.so")
        with open(library, "rb") as stream:
            header = stream.read(20)
        if len(header) != 20 or header[:4] != b"\x7fELF":
            raise ConanException("datefudge.so is not an ELF object")
        if header[4] != 2 or header[5] != 1:
            raise ConanException("datefudge.so is not little-endian ELF64")
        if int.from_bytes(header[18:20], "little") != 183:
            raise ConanException("datefudge.so is not an AArch64 object")
        self.output.success(
            "HarmonyOS-specific ABI test passed: ELF64 little-endian AArch64"
        )

    def _sign_ohos_executable(self):
        executable = os.path.join(self.cpp.build.bindirs[0], "test_datefudge")
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = (
            shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            raise ConanException("HarmonyOS ELF signing tools are unavailable")
        self.run(f'"{objcopy}" --remove-section .codesign "{executable}"')
        self.run(
            f'"{signer}" sign -inFile "{executable}" '
            f'-outFile "{executable}" -selfSign 1'
        )
        os.chmod(executable, 0o755)
