#!/usr/bin/env python3
"""Conan recipe for microlog 7.1.0.

microlog is a lightweight C logging library (successor of the classic
single-header log.c by rxi). Upstream builds with CMake as an INTERFACE
library: consumers compile src/ulog.c into their own target, and the
install tree ships `include/ulog.h`, `share/microlog/src/ulog.c` plus a
hand-written CMake config (micrologConfig.cmake + micrologTargets.cmake)
that re-creates the `microlog::microlog` static target from the installed
sources. This recipe uses the upstream CMake install unmodified, disables
the upstream unit tests during packaging, and exposes the installed CMake
config so downstream `find_package(microlog)` works out of the box.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class MicrologConan(ConanFile):
    name = "microlog"
    version = "7.1.0"
    description = "microlog: a generic multi-output C logging library (ulog)"
    license = "MIT"
    homepage = "https://github.com/an-dr/microlog"
    url = "https://github.com/an-dr/microlog"
    topics = ("logging", "log", "c")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream unit tests are exercised separately during adaptation;
        # keep the packaged build minimal (interface library install).
        tc.variables["ULOG_BUILD_TESTS"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # microlog ships its own CMake config; consumers use
        # find_package(microlog CONFIG) -> microlog::microlog (compiles
        # the installed ulog.c into their target, as upstream intends).
        # No cpp_info.libs: this is a source-distributed INTERFACE library
        # (no prebuilt .a/.so in the package); faking libs would break
        # downstream linking. See DRAFT-microlog-7.1.0-c-source-distributed-interface-recipe.
        self.cpp_info.set_property("cmake_file_name", "microlog")
        self.cpp_info.set_property("cmake_target_name", "microlog::microlog")
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.builddirs = ["lib/cmake/microlog"]