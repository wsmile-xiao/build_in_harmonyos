#!/usr/bin/env python3
"""Installed-package consumer tests for FluidSynth 2.5.7."""

import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import save


class FluidSynthTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        package_root = self.dependencies["fluidsynth"].package_folder
        toolchain = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            platform_modules = os.path.join(
                self.build_folder, "_cmake_modules"
            )
            save(
                self,
                os.path.join(
                    platform_modules, "Platform", "HarmonyOS.cmake"
                ),
                "include(Platform/Linux)\n",
            )
            toolchain.variables["CMAKE_MODULE_PATH"] = platform_modules
            toolchain.variables["CMAKE_SKIP_RPATH"] = True

        toolchain.variables["FLUIDSYNTH_PACKAGE_ROOT"] = package_root.replace(
            "\\", "/"
        )
        toolchain.variables["FLUIDSYNTH_INSTALLED_CMAKE_DIR"] = os.path.join(
            package_root, "lib", "cmake", "fluidsynth"
        ).replace("\\", "/")
        toolchain.variables["FLUIDSYNTH_INSTALLED_PKGCONFIG_DIR"] = os.path.join(
            package_root, "lib", "pkgconfig"
        ).replace("\\", "/")
        toolchain.variables["FLUIDSYNTH_EXPECT_SHARED"] = bool(
            self.dependencies["fluidsynth"].options.shared
        )
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        if not can_run(self):
            self.output.info(
                "NOT_RUN FLUIDSYNTH_TARGET_CONSUMERS=0/3 "
                "reason=cross_building"
            )
            return

        suffix = ".exe" if self.settings.os == "Windows" else ""
        for name in ("core_synth", "pkgconfig_soundfont"):
            executable = os.path.join(self.cpp.build.bindirs[0], name + suffix)
            self._sign_elf_for_ohos(executable)
            self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)

        cli = os.path.join(
            self.dependencies["fluidsynth"].package_folder,
            "bin",
            "fluidsynth" + suffix,
        )
        self.run(f'"{cli}" --version', env="conanrun", cwd=self.build_folder)
        if self.settings.os == "OHOS":
            self.output.info("FLUIDSYNTH_TARGET_CONSUMER_ELFS_SIGNED=2/2")
        self.output.info("FLUIDSYNTH_TARGET_CONSUMERS=3/3")

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as stream:
                return stream.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_elf_for_ohos(self, path):
        if self.settings.os != "OHOS":
            return

        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        readelf = "/data/service/hnp/bin/llvm-readelf"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        missing = [
            tool for tool in (objcopy, readelf, signer) if not os.path.isfile(tool)
        ]
        if missing:
            raise ConanInvalidConfiguration(
                "HarmonyOS ELF signing tools are missing: " + ", ".join(missing)
            )
        if not self._is_elf(path):
            raise ConanInvalidConfiguration(f"ELF signing input is invalid: {path}")

        clean_path = f"{path}.fluidsynth-codesign-clean"
        signed_path = f"{path}.fluidsynth-signed"
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
                timeout=60,
            ).stdout.splitlines()
            count = sum(".codesign" in line.split() for line in sections)
            if count != 1:
                raise ConanInvalidConfiguration(
                    f"signed ELF has {count} .codesign sections: {path}"
                )
            os.replace(signed_path, path)
            os.chmod(path, 0o755)
        finally:
            for temporary in (clean_path, signed_path):
                if os.path.exists(temporary):
                    os.remove(temporary)
