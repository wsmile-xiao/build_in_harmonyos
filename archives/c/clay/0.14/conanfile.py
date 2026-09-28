#!/usr/bin/env python3
"""Conan recipe — clay 0.14

Clay (short for C Layout) is a high-performance 2D UI layout library,
shipped as a single ~4k-LOC clay.h header with zero dependencies (it
does not even require the C standard library). One compilation unit
must define CLAY_IMPLEMENTATION before including clay.h; the recipe
compiles that TU into a static library and installs the header, so
consumers can just link clay::clay instead of managing the
implementation macro themselves.

Upstream test posture: no registered ctest suite — CI (GitHub Actions)
builds the CMake project (cpp-project-example under ASan) as the
validation; the "tests" directory only contains a docker-compose build
smoke for gcc 9.4. Both were re-executed locally on the OHOS device
(see notes.md); test_package adds a layout-assertion consumer suite.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy


class ClayConan(ConanFile):
    name = "clay"
    version = "0.14"
    description = "High performance 2D UI layout library (single header, zero dependencies)"
    license = "Zlib"
    homepage = "https://github.com/nicbarker/clay"
    url = "https://github.com/nicbarker/clay"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "fPIC": [True, False],
        "shared": [True, False],
    }
    default_options = {
        "fPIC": True,
        "shared": False,
    }

    implements = ["auto_shared_fpic"]

    exports_sources = "packaging/*", "clay_impl.c", "patches/*"

    def layout(self):
        cmake_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: flags/toolchain come from the Conan toolchain.
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        # Configure from the recipe's packaging project — NOT the build
        # root: `get(strip_root=True)` extracts the upstream tree at the
        # build root, whose own CMakeLists defaults to building every
        # example (SDL2/SDL3/raylib FetchContent downloads) and breaks
        # on OHOS. The packaging project builds clay_impl.c only.
        cmake.configure(
            variables={"CLAY_SRC_DIR": self.source_folder},
            cli_args=[f"-S {os.path.join(self.source_folder, 'packaging', 'cmake')}"],
        )
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.md",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "clay")
        self.cpp_info.set_property("cmake_target_name", "clay::clay")
        self.cpp_info.libs = ["clay"]
        self.cpp_info.includedirs = ["include"]
