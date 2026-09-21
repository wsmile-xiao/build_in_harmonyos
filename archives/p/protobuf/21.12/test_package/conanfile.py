#!/usr/bin/env python3
"""Conan consumer tests for protobuf 21.12 (CMake).

Two independent entries against the *installed* package:

  * ctest suite (test_protobuf.cpp) - generic consumer scenarios:
    dynamic/pool/arena/parse_error plus `protoc --version`;
  * test_ohos.py - HarmonyOS-specific tests (R53), pure Python with no
    readelf/objdump dependency: libprotobuf.a archive + member objects
    are ELF64/AArch64, protoc is ELF64/AArch64 with the OHOS musl
    interpreter and .codesign section and no RPATH/RUNPATH, and protoc
    really runs (--version + C++ code generation over a fixture .proto).
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class ProtobufTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        protobuf = self.dependencies["protobuf"]
        tc = CMakeToolchain(self)
        tc.variables["Protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf"
        ).replace("\\", "/")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run(
                "ctest --output-on-failure --no-tests=error",
                cwd=self.build_folder,
                env="conanrun",
            )
            self._test_ohos_specific()

    def _test_ohos_specific(self):
        # R53: dedicated HarmonyOS assertions against the packaged
        # artifacts; runs the packaged protoc for real (version +
        # fixture .proto -> generated C++ sources).
        if str(self.settings.os) != "OHOS":
            return
        protobuf = self.dependencies["protobuf"]
        package_folder = protobuf.package_folder
        tmp_dir = os.path.join(self.build_folder, "ohos-specific-test")
        python = os.environ.get("CONAN_TEST_PYTHON3", "") or "python3"
        self.run(
            '"{}" "{}" --tmp-dir "{}" "{}" "{}"'.format(
                python,
                os.path.join(self.source_folder, "test_ohos.py"),
                tmp_dir,
                os.path.join(package_folder, "bin", "protoc"),
                os.path.join(package_folder, "lib", "libprotobuf.a"),
            ),
            env="conanrun",
        )
