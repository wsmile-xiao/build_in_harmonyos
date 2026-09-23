#!/usr/bin/env python3
"""Conan recipe for miniupnpc 2.3.3.1 — UPnP IGD client lightweight library (upstream 2.3.3).

Build system: CMake (miniupnpc ships both Makefile and CMakeLists.txt).
miniupnpc is a pure C library with no external dependencies.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MiniupnpcConan(ConanFile):
    name = "miniupnpc"
    version = "2.3.3.1"
    description = "UPnP IGD client lightweight library"
    license = "BSD-3-Clause"
    homepage = "https://miniupnp.tuxfamily.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "build_samples": [True, False],
    }
    default_options = {
        "shared": False,
        "build_samples": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["UPNPC_BUILD_STATIC"] = not self.options.shared
        tc.variables["UPNPC_BUILD_SHARED"] = self.options.shared
        tc.variables["UPNPC_BUILD_TESTS"] = True
        tc.variables["UPNPC_BUILD_SAMPLE"] = self.options.build_samples
        # R32: support both Linux and OHOS
        if self.settings.os in ("Linux", "OHOS"):
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # UPNPC_BUILD_TESTS registers the upstream CTest suite. Run all seven
        # tests, including the local loopback miniwget test. --no-tests=error
        # fails the build if the suite ever registers zero test cases.
        self.run("ctest --output-on-failure --no-tests=error", cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["miniupnpc"]
        if not self.options.shared:
            self.cpp_info.defines.append("MINIUPNP_STATICLIB")
