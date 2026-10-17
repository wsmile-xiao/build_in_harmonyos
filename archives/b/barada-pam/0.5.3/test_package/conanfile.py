#!/usr/bin/env python3
"""Consumer test for the installed command and PAM module."""

import io
import os
import platform

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BaradaPamTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The consumer compiles against PAM's public module ABI while loading
        # pam_barada.so from the tested package.
        self.requires("linux-pam/1.7.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        pam = self.dependencies["linux-pam"]
        pam_include = pam.cpp_info.includedirs[0]
        tc = CMakeToolchain(self)
        tc.variables["BARADA_PAM_INCLUDE_DIR"] = pam_include
        if self._is_wsl_ohos():
            # WSL has qemu-aarch64-static but no OHOS musl dynamic loader.
            tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-static"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning(
                "SKIP: test_package runtime checks require an executable target "
                "environment; the current cross-compilation environment cannot run OHOS binaries."
            )
            return

        package = self.dependencies["barada-pam"]
        module = os.path.join(
            package.package_folder, "lib", "security", "pam_barada.so"
        )
        if not self._is_wsl_ohos():
            executable = os.path.join(
                self.cpp.build.bindirs[0], "test_barada_pam"
            )
            self.run(f'"{executable}" "{module}"', env="conanrun")

        # Use an invalid user so the installed command exercises entropy,
        # Boost.Filesystem, and argument handling without modifying
        # /etc/barada.d. The WSL package build makes this CLI static because
        # qemu cannot load OHOS dynamic ELF files.
        barada_add = os.path.join(package.package_folder, "bin", "barada-add")
        output = io.StringIO()
        self.run(
            f'"{barada_add}" __barada_test_invalid_user__ 123',
            env="conanrun",
            stdout=output,
            stderr=output,
        )
        diagnostic = output.getvalue()
        self.output.info(f"barada-add diagnostic: {diagnostic.strip()}")
        if "valid username" not in diagnostic.lower():
            raise ConanException(
                "barada-add rejected the invalid username without the expected diagnostic: "
                f"{diagnostic.strip()}"
            )

    def _is_wsl_ohos(self):
        return (
            str(self.settings.os) == "OHOS"
            and platform.system() == "Linux"
            and "microsoft-standard" in platform.release().lower()
        )
