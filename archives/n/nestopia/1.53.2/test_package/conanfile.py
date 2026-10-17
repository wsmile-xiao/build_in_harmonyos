#!/usr/bin/env python3
"""Installed-package consumer test for Nestopia 1.53.2 (headless core API)."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class NestopiaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The core archive references zlib symbols; link it explicitly so the
        # static libnestopia_core.a resolves in the right order.
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            toolchain.cache_variables["CMAKE_SKIP_RPATH"] = True
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # The Conan build reports cross_building for OHOS-on-OHOS builds
        # (can_run() is False on this platform), but the produced binary runs
        # on this host once signed.  Always execute the smoke test.
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executable = os.path.join(
            self.cpp.build.bindirs[0], "nestopia_core_smoke" + suffix
        )
        self._sign_elf_for_ohos(executable)
        self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)

    def _sign_elf_for_ohos(self, path):
        if str(self.settings.os) != "OHOS":
            return

        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(path):
            raise ConanInvalidConfiguration(f"consumer executable is missing: {path}")
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                "HarmonyOS ELF signing tools are required for target execution"
            )

        clean_path = f"{path}.codesign-clean"
        signed_path = f"{path}.signed"
        for temporary in (clean_path, signed_path):
            if os.path.exists(temporary):
                os.remove(temporary)
        try:
            self.run(
                f"{shlex.quote(objcopy)} --remove-section .codesign "
                f"{shlex.quote(path)} {shlex.quote(clean_path)}"
            )
            self.run(
                f"{shlex.quote(signer)} sign -inFile {shlex.quote(clean_path)} "
                f"-outFile {shlex.quote(signed_path)} -selfSign 1"
            )
            os.replace(signed_path, path)
            os.chmod(path, 0o755)
        finally:
            for temporary in (clean_path, signed_path):
                if os.path.exists(temporary):
                    os.remove(temporary)