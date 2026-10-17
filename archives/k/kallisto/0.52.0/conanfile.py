#!/usr/bin/env python3
"""Conan recipe for kallisto 0.52.0 — RNA-seq quantifier (C++17, CMake).

HarmonyOS PC adaptation:
- CMake >= 3.10 (patched from 3.0.0, ExternalProject parsing on OHOS needs it)
- ENABLE_AVX2=OFF + COMPILATION_ARCH=OFF (aarch64, no AVX2/arch-specific codegen)
- USE_BAM=OFF (htslib optional; core quantification does not need it)
- USE_HDF5=OFF (optional; bustools workflows need it, plain quant does not)
- bifrost (ext/bifrost) built via upstream ExternalProject_Add from bundled sources
- zlib from conan (requires zlib/1.3.2, published in main)
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, copy
from conan.errors import ConanException


class KallistoConan(ConanFile):
    name = "kallisto"
    version = "0.52.0"
    description = "Quantify abundances of transcripts from RNA-Seq data"
    license = "BSD-2-Clause"
    homepage = "https://pachterlab.github.io/kallisto/"
    url = "https://github.com/pachterlab/kallisto"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "patches/*"

    def requirements(self):
        self.requires("zlib/1.3.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # aarch64: no AVX2, no arch-specific compilation flags
        tc.variables["ENABLE_AVX2"] = "OFF"
        tc.variables["COMPILATION_ARCH"] = "OFF"
        # htslib (BAM) and HDF5 are optional; keep core quant build minimal
        tc.variables["USE_BAM"] = "OFF"
        tc.variables["USE_HDF5"] = "OFF"
        # build & run upstream unit tests (Catch2, BUILT_TESTING target)
        tc.variables["BUILD_TESTING"] = "ON"
        # bifrost is built via ExternalProject as a SEPARATE cmake process,
        # which cannot see the top-level ZLIB find_package result — inject
        # the conan zlib paths explicitly (0006 patch passes them on).
        zlib = self.dependencies["zlib"]
        zlib_pkg = zlib.package_folder
        tc.variables["BIFROST_ZLIB_INCLUDE"] = os.path.join(zlib_pkg, "include")
        tc.variables["BIFROST_ZLIB_LIBRARY"] = os.path.join(zlib_pkg, "lib", "libz.a")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if not os.path.isdir(os.path.join(self.source_folder, "src")):
            raise ConanException("kallisto source tree not found")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游单元测试（Catch2，unit_tests/）实测运行，回填真实通过率（规则 4）
        # func_tests/runtests.sh 的功能测试数据（aa_ref.fasta 等）未随上游
        # sdist 打包（0 个数据文件），无法运行，故实测 unit_tests 部分。
        tests_bin = os.path.join(self.build_folder, "unit_tests", "tests")
        if os.path.isfile(tests_bin):
            self.run(tests_bin)

    def package(self):
        copy(self, "kallisto", src=os.path.join(self.build_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 附带上游 unit_tests input 数据，供 test_package 做真实 index+quant 冒烟
        src_input = os.path.join(self.source_folder, "unit_tests", "input")
        if os.path.isdir(src_input):
            copy(self, "*", src=src_input,
                 dst=os.path.join(self.package_folder, "share", "kallisto",
                                  "unit_tests", "input"))

    def package_info(self):
        self.cpp_info.libs = []
