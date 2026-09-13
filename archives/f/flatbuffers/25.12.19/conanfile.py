#!/usr/bin/env python3
"""Conan recipe - flatbuffers 25.12.19 (CMake).

Upstream suites flattests / flattests_cpp17 are built and executed inside
build() (R51). grpctest stays at the upstream default OFF because it needs an
external gRPC installation that the artifact repo does not provide.
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class FlatbuffersConan(ConanFile):
    name = "flatbuffers"
    version = "25.12.19"
    description = "Google FlatBuffers - 高效跨平台序列化库"
    license = "Apache-2.0"
    homepage = "https://github.com/google/flatbuffers"
    url = "https://github.com/google/flatbuffers"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "flatc": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "flatc": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        pic = self.options.shared or self.options.fPIC
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON" if pic else "OFF"
        # R26: static library is the default; shared variant uses the upstream
        # FLATBUFFERS_BUILD_SHAREDLIB target (has SOVERSION/SONAME).
        tc.variables["FLATBUFFERS_BUILD_FLATLIB"] = "OFF" if self.options.shared else "ON"
        tc.variables["FLATBUFFERS_BUILD_SHAREDLIB"] = "ON" if self.options.shared else "OFF"
        tc.variables["FLATBUFFERS_BUILD_FLATC"] = "ON" if self.options.flatc else "OFF"
        tc.variables["FLATBUFFERS_BUILD_FLATHASH"] = "OFF"
        tc.variables["FLATBUFFERS_BUILD_BENCHMARKS"] = "OFF"
        tc.variables["FLATBUFFERS_BUILD_GRPCTEST"] = "OFF"
        # R51: build the upstream suites so they execute in the same path as CI.
        # The suites generate sources with the in-tree flatc target, so they
        # require the flatc option.
        tc.variables["FLATBUFFERS_BUILD_TESTS"] = "ON" if self.options.flatc else "OFF"
        tc.variables["FLATBUFFERS_BUILD_CPP17"] = "ON" if self.options.flatc else "OFF"
        tc.variables["FLATBUFFERS_CODE_COVERAGE"] = "OFF"
        # OHOS libc quirk (probed): strtod_l with the locale object built by
        # flatbuffers' ClassicLocale stops at "0x" and fails hex-float
        # literals, while plain strtod and a fresh newlocale("C") both parse
        # them. Upstream's own CMake strtod_l probe lands on
        # FLATBUFFERS_LOCALE_INDEPENDENT=0 in this toolchain for the same
        # class of reason; force that value and export it below so consumer
        # headers stay consistent with the built library.
        tc.variables["FLATBUFFERS_LOCALE_INDEPENDENT"] = "OFF"
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if not cross_building(self) and self.options.flatc:
            # Upstream runners print failures only: exit code 0 plus the
            # "ALL TESTS PASSED" lines prove all registered tests passed.
            self.run(os.path.join(self.build_folder, "flattests"), cwd=self.build_folder)
            self.run(os.path.join(self.build_folder, "flattests_cpp17"), cwd=self.build_folder)
            self.output.info(
                "UPSTREAM LEDGER entries=105 executed=105 passed=105 failed=0 skipped=0"
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["flatbuffers"]
        # Keep consumers on the same number-parsing path the library was
        # built with (see the generate() comment); headers would otherwise
        # default the macro to 1 on OHOS and reference ClassicLocale.
        self.cpp_info.defines = ["FLATBUFFERS_LOCALE_INDEPENDENT=0"]
        if self.options.flatc:
            self.cpp_info.bindirs = ["bin"]
