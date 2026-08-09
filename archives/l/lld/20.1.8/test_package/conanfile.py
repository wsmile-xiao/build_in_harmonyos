#!/usr/bin/env python3
"""Conan consumer test - LLD 20.1.8 command-line linker."""

import os
import stat
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv


class LldTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        package_bin = os.path.join(
            self.dependencies["lld"].package_folder,
            "bin",
        )
        tc = CMakeToolchain(self)
        tc.cache_variables["LLD_EXECUTABLE"] = os.path.join(
            package_bin,
            "ld.lld",
        )
        tc.generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])
        executable = os.path.join(self.build_folder, "test_lld")
        self._sign_ohos_executable(executable)

    def _sign_ohos_executable(self, executable):
        if str(self.settings.os) != "OHOS":
            return
        if not os.path.isfile(executable):
            raise ConanException(f"Consumer executable not found: {executable}")

        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(f"Required OHOS signing tool not found: {tool}")

        self.run(f'"{objcopy}" --remove-section .codesign "{executable}"')
        signed = f"{executable}.signed"
        last_error = None
        for attempt in range(3):
            if os.path.exists(signed):
                os.remove(signed)
            try:
                self.run(
                    f'"{signer}" sign -inFile "{executable}" '
                    f'-outFile "{signed}" -selfSign 1'
                )
            except ConanException as error:
                last_error = error
            else:
                if os.path.isfile(signed) and os.path.getsize(signed) > 0:
                    break
                last_error = ConanException(
                    f"OHOS signer did not create non-empty output: {signed}"
                )
            if attempt < 2:
                time.sleep(1)
        else:
            if os.path.exists(signed):
                os.remove(signed)
            raise ConanException(
                f"Unable to sign consumer executable after 3 attempts: {executable}"
            ) from last_error

        os.replace(signed, executable)
        mode = os.stat(executable).st_mode
        os.chmod(
            executable,
            mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
        )

    def test(self):
        if can_run(self):
            package_bin = os.path.join(
                self.dependencies["lld"].package_folder,
                "bin",
            )
            commands = (
                ("lld", "-flavor gnu --version"),
                ("ld.lld", "--version"),
                ("lld-link", "--version"),
                ("ld64.lld", "--version"),
                ("wasm-ld", "--version"),
            )
            for command, arguments in commands:
                executable = os.path.join(package_bin, command)
                self.run(f'"{executable}" {arguments}', env="conanrun")
            executable = os.path.join(self.build_folder, "test_lld")
            self.run(f'"{executable}"', env="conanrun")
