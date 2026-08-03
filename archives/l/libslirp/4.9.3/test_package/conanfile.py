#!/usr/bin/env python3
"""Installed-package consumer for libslirp 4.9.3."""

import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibslirpTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            toolchain.cache_variables["CMAKE_SKIP_RPATH"] = True
        toolchain.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning(
                "Cross build: the consumer linked but was not run on this host."
            )
            return

        suffix = ".exe" if self.settings.os == "Windows" else ""
        executable = os.path.join(
            self.cpp.build.bindirs[0], "libslirp_consumer" + suffix
        )
        self._sign_elf_for_ohos(executable)
        self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)

    def _sign_elf_for_ohos(self, path):
        if self.settings.os != "OHOS":
            return

        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        readelf = "/data/service/hnp/bin/llvm-readelf"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(path):
            raise ConanInvalidConfiguration(f"consumer executable is missing: {path}")
        if any(not os.path.isfile(tool) for tool in (objcopy, readelf, signer)):
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
            sections = subprocess.run(
                [readelf, "-SW", signed_path],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            ).stdout
            if sections.count(".codesign") != 1:
                raise ConanInvalidConfiguration(
                    "signed consumer has invalid .codesign count"
                )
            os.remove(path)
            os.replace(signed_path, path)
            os.chmod(path, 0o755)
        finally:
            for temporary in (clean_path, signed_path):
                if os.path.exists(temporary):
                    os.remove(temporary)
