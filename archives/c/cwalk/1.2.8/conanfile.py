#!/usr/bin/env python3
"""Conan recipe for cwalk 1.2.8 — ported from archived 1.2.9 (CI-proven) + G1-required methods."""

import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches


class CwalkConan(ConanFile):
    name = "cwalk"
    version = "1.2.8"
    description = "Cross-platform path manipulation library for C and C++"
    license = "MIT"
    homepage = "https://github.com/likle/cwalk"
    url = "https://github.com/likle/cwalk"
    topics = ("path", "filesystem", "c", "cross-platform")
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "cwalk 1.2.8 currently supports only OHOS armv8"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = False
        toolchain.variables["ENABLE_TESTS"] = True
        toolchain.variables["ENABLE_COVERAGE"] = False
        toolchain.variables["ENABLE_SANITIZER"] = ""
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # Upstream test runner must be signed before ctest on OHOS (E-family: unsigned ELF cannot execute)
        test_binary = next(Path(self.build_folder).rglob("cwalktest"), None)
        if test_binary is None or not test_binary.is_file():
            raise ConanInvalidConfiguration("upstream cwalktest executable was not built")
        self._sign(test_binary)
        self.run(
            f'ctest --test-dir "{self.build_folder}" --output-on-failure',
            env="conanrun",
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["cwalk"]
        self.cpp_info.set_property("cmake_file_name", "Cwalk")
        self.cpp_info.set_property("cmake_target_name", "cwalk::cwalk")
        self.cpp_info.set_property("pkg_config_name", "cwalk")

    @staticmethod
    def _sign(executable):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required to execute upstream tests on OHOS"
            )
        signed = executable.with_suffix(executable.suffix + ".signed")
        if os.path.isfile(objcopy):
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", str(executable)],
                check=False,
            )
        subprocess.run(
            [signer, "sign", "-inFile", str(executable), "-outFile", str(signed),
             "-selfSign", "1"],
            check=True,
        )
        shutil.move(signed, executable)
        os.chmod(executable, 0o755)
