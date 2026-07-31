#!/usr/bin/env python3
"""Installed-package consumer for opusfile 0.12."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class OpusfileTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("libogg/1.3.5")
        self.requires("opus/1.5.2.1")

    def layout(self):
        cmake_layout(self)

    @staticmethod
    def _dependency_library(dependency):
        candidates = []
        for libdir in dependency.cpp_info.libdirs:
            for library in dependency.cpp_info.libs:
                for filename in (f"lib{library}.so", f"lib{library}.a"):
                    path = os.path.join(dependency.package_folder, libdir, filename)
                    if os.path.isfile(path):
                        candidates.append(path)
        if len(candidates) != 1:
            raise ConanException(
                f"Expected one library for {dependency.ref}, got {candidates}"
            )
        return candidates[0].replace("\\", "/")

    def generate(self):
        dependencies = CMakeDeps(self)
        dependencies.set_property("libogg", "cmake_file_name", "Ogg")
        dependencies.set_property("libogg", "cmake_target_name", "Ogg::ogg")
        dependencies.set_property("opus", "cmake_file_name", "Opus")
        dependencies.set_property("opus", "cmake_target_name", "Opus::opus")
        dependencies.generate()
        toolchain = CMakeToolchain(self)
        toolchain.variables["OPUSFILE_TEST_OGG_INCLUDE"] = os.path.join(
            self.dependencies["libogg"].package_folder,
            "include",
        ).replace("\\", "/")
        toolchain.variables["OPUSFILE_TEST_OPUS_INCLUDE"] = os.path.join(
            self.dependencies["opus"].package_folder,
            "include",
        ).replace("\\", "/")
        toolchain.variables["OPUSFILE_TEST_OGG_LIBRARY"] = self._dependency_library(
            self.dependencies["libogg"]
        )
        toolchain.variables["OPUSFILE_TEST_OPUS_LIBRARY"] = self._dependency_library(
            self.dependencies["opus"]
        )
        toolchain.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    @staticmethod
    def _ohos_tool(name):
        path = shutil.which(name) or os.path.join("/data/service/hnp/bin", name)
        if not os.path.isfile(path):
            raise ConanException(f"Required OHOS tool is missing: {name}")
        return path

    def _sign_ohos_elf(self, path):
        readelf = self._ohos_tool("llvm-readelf")
        objcopy = self._ohos_tool("llvm-objcopy")
        signer = self._ohos_tool("binary-sign-tool")
        sections = subprocess.run(
            [readelf, "-SW", path],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        codesign_count = sections.count(".codesign")
        if codesign_count == 1:
            self.output.info(f"Preserving existing .codesign section: {path}")
            return
        if codesign_count != 0:
            raise ConanException(f"Consumer has invalid .codesign count: {codesign_count}")
        clean = path + ".codesign-clean"
        signed = path + ".opusfile-signed"
        for generated in (clean, signed):
            if os.path.exists(generated):
                os.remove(generated)
        try:
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", path, clean],
                check=True,
                timeout=30,
            )
            subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    clean,
                    "-outFile",
                    signed,
                    "-selfSign",
                    "1",
                ],
                check=True,
                timeout=60,
            )
            sections = subprocess.run(
                [readelf, "-SW", signed],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            ).stdout
            if sections.count(".codesign") != 1:
                raise ConanException("Signed consumer has invalid .codesign count")
            os.chmod(signed, (os.stat(path).st_mode & 0o777) | 0o055)
            os.replace(signed, path)
        finally:
            for generated in (clean, signed):
                if os.path.exists(generated):
                    os.remove(generated)

    def test(self):
        if not can_run(self):
            self.output.info("NOT_RUN: target consumer execution is unavailable while cross-building")
            return
        executable = os.path.join(self.cpp.build.bindir, "opusfile_consumer")
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(executable)
        self.run(f'"{executable}"', env="conanrun", cwd=self.cpp.build.bindir)
