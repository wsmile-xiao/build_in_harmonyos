#!/usr/bin/env python3
"""Conan test_package -- kxl 1.2.4 consumer link/API smoke test.

Statically links the test binary against libKXL_static.a (the OHOS
loader refuses to dlopen() shared libraries from /storage/... paths,
so a dlopen()-based runtime smoke test is not viable on this device
class).  The static-link build still proves that the kxl recipe's
transitive deps (libx11, libxcb, libxau, libxdmcp, xtrans) were
correctly wired into the consumer link line.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KxlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # kxl's KXL.h transitively pulls in <X11/Xlib.h>, so the test
        # consumer needs libx11's include dir at compile time.  Conan
        # 2.x's CMakeDeps wipes the *INCLUDE_DIRS_RELEASE variable for
        # any requirement that doesn't explicitly request headers=True
        # at the immediate consumer level (see conan/tools/cmake/
        # cmakedeps/templates/target_data.py -- `if require and not
        # require.headers: self.include_paths = ""`).
        self.requires("libx11/6.4.0", headers=True, libs=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # OHOS SDK toolchain sets CMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY,
        # which masks the CMAKE_PREFIX_PATH entry that conan's
        # CMakeDeps generator writes the kxl-config.cmake /
        # libx11-config.cmake / ... into.  Flip every *_MODE_* to BOTH
        # so find_package(<dep>) can locate the <dep>-config.cmake
        # files emitted under <build>/generators/.
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
            tc.variables["CMAKE_FIND_ROOT_PATH_MODE_LIBRARY"] = "BOTH"
            tc.variables["CMAKE_FIND_ROOT_PATH_MODE_INCLUDE"] = "BOTH"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Just exec the statically-linked binary.  No dlopen(), no
        # LD_LIBRARY_PATH injection -- the libKXL.a symbols are baked
        # into the .text segment at link time, so the OHOS loader's
        # namespace ACL on /storage/ paths doesn't apply.
        self.run("./test_kxl", env="conanrun")