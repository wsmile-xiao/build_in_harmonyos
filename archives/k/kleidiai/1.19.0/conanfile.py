#!/usr/bin/env python3
"""Conan 2 recipe for KleidiAI 1.19.0 (Arm AI micro-kernels)."""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)


class KleidiaiConan(ConanFile):
    name = "kleidiai"
    version = "1.19.0"
    description = (
        "KleidiAI — Arm-optimized micro-kernels (matmul, packing, "
        "quantization) for AI/ML inference on Arm CPUs"
    )
    license = "Apache-2.0"
    homepage = "https://gitlab.arm.com/kleidi/kleidiai"
    url = "https://github.com/ARM-software/KleidiAI"
    topics = ("arm", "aarch64", "micro-kernel", "matmul", "simd", "sve")
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["KLEIDIAI_BUILD_TESTS"] = True
        tc.variables["KLEIDIAI_BUILD_BENCHMARK"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        self._patch_gtest_tmpdir()
        cmake.build()
        if not cross_building(self):
            # Run the monolithic GoogleTest binary directly instead of ctest:
            # ctest runs every discovered test in its own process (twice, since
            # the build also produces per-file executables), which is far too
            # slow for KleidiAI's ~58k parameterized cases.
            test_bin = os.path.join(self.build_folder, "kleidiai_test")
            self.run(f'"{test_bin}" --gtest_brief=1', env="conanbuild")

    def _patch_gtest_tmpdir(self):
        # HarmonyOS mounts /tmp read-only, but googletest's CapturedStream
        # hard-codes "/tmp/" for its capture files, so any test that writes to
        # stdout aborts. Redirect it to a writable folder inside the build dir.
        gtest_port = os.path.join(
            self.build_folder,
            "_deps",
            "googletest-src",
            "googletest",
            "src",
            "gtest-port.cc",
        )
        if os.path.exists(gtest_port):
            tmpdir = os.path.join(self.build_folder, "gtest_tmp")
            os.makedirs(tmpdir, exist_ok=True)
            replace_in_file(
                self,
                gtest_port,
                'name_template = "/tmp/";',
                f'name_template = "{tmpdir}/";',
            )

    def package(self):
        CMake(self).install()
        copy(
            self,
            "*.txt",
            src=os.path.join(self.source_folder, "LICENSES"),
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["kleidiai"]
        self.cpp_info.set_property("cmake_file_name", "KleidiAI")
        self.cpp_info.set_property("cmake_target_name", "KleidiAI::kleidiai")
