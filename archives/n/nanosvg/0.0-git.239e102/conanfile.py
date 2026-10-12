#!/usr/bin/env python3
"""Conan recipe for nanosvg 0.0-git.239e102.

nanosvg is a simple stupid SVG parser + anti-aliased rasterizer by
Mikko Mononen (zlib license). It ships as two single-header libraries:

  * src/nanosvg.h     — parser     (NANOSVG_IMPLEMENTATION activates)
  * src/nanosvgrast.h — rasterizer (NANOSVGRAST_IMPLEMENTATION activates)

Upstream provides a working CMakeLists.txt which this recipe uses as-is:
it generates two thin static libraries via configure_file (nanosvg.c from
nanosvg.h with NANOSVG_IMPLEMENTATION, nanosvgrast.c from nanosvgrast.h
with NANOSVGRAST_IMPLEMENTATION), installs the two public headers to
include/nanosvg/ and exports NanoSVG::nanosvg / NanoSVG::nanosvgrast.

Zero patches, zero source modifications. Zero third-party dependencies
(libc/libm only). Upstream registers no tests (no enable_testing /
add_test in the build; example/ is a manually built demo, not a test
suite) — consumer-side assertions run in test_package/.

Upstream snapshot: master @ 239e102ec2c691f2902e20ace2ed36ee4a35cfe6
(the 7-hex prefix 239e102 is the version tag per the master-only
repository versioning rule 0.0-git.{hash7}; verified via git ls-remote).
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class NanosvgConan(ConanFile):
    name = "nanosvg"
    version = "0.0-git.239e102"
    description = "Simple stupid SVG parser and rasterizer (two single-header libraries)"
    license = "Zlib"
    homepage = "https://github.com/memononen/nanosvg"
    url = "https://github.com/memononen/nanosvg"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def configure(self):
        # R32: platform check must use `in`, never `==`
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"nanosvg only supports Linux/OHOS, current: {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # conandata URL list: mirror first, official fallback (Conan 2 get()
        # tries the list in order; sha256 verified for both)
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake >= 4 workers break the compiler check on the OHOS-adapted
        # CMAKE_SYSTEM_NAME=HarmonyOS mapping (no Platform/HarmonyOS module
        # in CMake). OHOS is POSIX: force the Linux platform (chain-wide
        # convention; abcmidi/adios2/kpeople5 precedent).
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        # R26: static by default — no system-name .so collision risk
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        # upstream implementation TUs are plain C99
        tc.variables["CMAKE_C_STANDARD"] = "99"
        tc.variables["CMAKE_C_STANDARD_REQUIRED"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Dual-library structure mirrors the upstream CMake export:
        # find_package(NanoSVG) → NanoSVG::nanosvg / NanoSVG::nanosvgrast
        # Upstream installs the headers to include/nanosvg/ and its exported
        # targets put that dir on the include path, so consumers write
        # #include <nanosvg.h> / <nanosvgrast.h> (not <nanosvg/nanosvg.h>).
        self.cpp_info.set_property("cmake_file_name", "NanoSVG")
        nanosvg = self.cpp_info.components["nanosvg"]
        nanosvg.set_property("cmake_target_name", "NanoSVG::nanosvg")
        nanosvg.libs = ["nanosvg"]
        nanosvg.includedirs = ["include/nanosvg"]
        # musl/OHOS folds libm into libc; the -lm link stays harmless there
        nanosvg.system_libs = ["m"]
        rast = self.cpp_info.components["nanosvgrast"]
        rast.set_property("cmake_target_name", "NanoSVG::nanosvgrast")
        rast.libs = ["nanosvgrast"]
        rast.includedirs = ["include/nanosvg"]
        rast.requires = ["nanosvg"]
