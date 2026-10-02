#!/usr/bin/env python3
"""Installed-package consumer test for libcamera 0.7.2."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibcameraTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def configure(self):
        # The installed library is built as C++20; compile the public consumer
        # with the same language mode instead of inheriting the OHOS profile's
        # older default.
        self.settings.compiler.cppstd = "20"

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        virtual_run_env = VirtualRunEnv(self)
        run_environment = virtual_run_env.environment()
        if self.settings.os == "OHOS":
            package = self.dependencies["libcamera"].package_folder
            run_environment.define(
                "LIBCAMERA_IPA_MODULE_PATH",
                os.path.join(package, "lib", "libcamera", "ipa"),
            )
            run_environment.define(
                "LIBCAMERA_IPA_PROXY_PATH",
                os.path.join(package, "bin", "libcamera"),
            )
        virtual_run_env.generate(scope="run")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        temporary = path + ".libcamera-signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", temporary,
             "-selfSign", "1"], check=True, timeout=60
        )
        sections = subprocess.run(
            [readelf, "-SW", temporary], check=True, capture_output=True,
            text=True, timeout=30
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("Signed consumer has invalid .codesign count")
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o111)
        os.replace(temporary, path)

    def test(self):
        if not can_run(self):
            raise ConanException("libcamera consumer test cannot run for this target")
        executable = os.path.join(self.cpp.build.bindir, "test_libcamera")
        if not os.path.isfile(executable):
            raise ConanException(f"consumer executable not found: {executable}")
        if self.settings.os == "OHOS":
            self._sign_ohos_elf(executable)
        self.run(f'"{executable}"', env="conanrun")
