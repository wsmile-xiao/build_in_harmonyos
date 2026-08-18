#!/usr/bin/env python3
"""Conan recipe for exiv2 0.28.7 — CMake project.

exiv2 is a C++ library and command-line tool to read, write, delete and
modify Exif, IPTC, XMP and ICC image metadata.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rm, rmdir, replace_in_file
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class Exiv2Conan(ConanFile):
    name = "exiv2"
    version = "0.28.7"
    description = "EXIF/IPTC/XMP image metadata library and command-line tool"
    license = "GPL-2.0"
    homepage = "https://github.com/Exiv2/exiv2"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("expat/2.8.2.1")
        self.test_requires("gtest/1.17.0")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: static by default; only honor shared option
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Metadata support
        tc.variables["EXIV2_ENABLE_XMP"] = "ON"
        tc.variables["EXIV2_ENABLE_PNG"] = "ON"
        # Disable optional features unavailable on OHOS / not required
        tc.variables["EXIV2_ENABLE_BMFF"] = "OFF"
        tc.variables["EXIV2_ENABLE_BROTLI"] = "OFF"
        tc.variables["EXIV2_ENABLE_INIH"] = "OFF"
        tc.variables["EXIV2_ENABLE_VIDEO"] = "OFF"
        tc.variables["EXIV2_ENABLE_WEBREADY"] = "OFF"
        tc.variables["EXIV2_ENABLE_CURL"] = "OFF"
        tc.variables["EXIV2_ENABLE_NLS"] = "OFF"
        tc.variables["EXIV2_ENABLE_EXTERNAL_XMP"] = "OFF"
        # Build the exiv2 command-line tool
        tc.variables["EXIV2_BUILD_EXIV2_COMMAND"] = "ON"
        # Disable tests / samples / docs / fuzz
        tc.variables["EXIV2_BUILD_SAMPLES"] = "OFF"
        tc.variables["EXIV2_BUILD_UNIT_TESTS"] = "ON"
        tc.variables["EXIV2_BUILD_FUZZ_TESTS"] = "OFF"
        tc.variables["EXIV2_BUILD_DOC"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # exiv2 unitTests link GTest::gmock_main, but gtest/1.17.0 conan recipe
        # only declares a single gtest component (libs: gtest, gtest_main, gmock)
        # and does not generate a GTest::gmock_main CMake target. Replace it with
        # the three real targets: GTest::gtest + GTest::gmock + GTest::gtest_main
        # (gtest_main provides the main() entry point).
        replace_in_file(self,
            os.path.join(self.source_folder, "unitTests", "CMakeLists.txt"),
            "GTest::gmock_main",
            "GTest::gtest GTest::gmock GTest::gtest_main")
        # The root CMakeLists.txt registers 5 pytest-based ctest targets
        # (bugfixTests, lensTests, tiffTests, versionTests, regressionTests)
        # guarded by `if (Python3_Interpreter_FOUND)`. These require Python3 +
        # EXIV2_BUILD_SAMPLES binaries + test/data files, none of which are
        # available in the OHOS build environment. Disable their registration
        # so cmake.test() only runs the GTest-based unitTests target.
        # Conan's replace_in_file has no replace_all, so call twice (the
        # pattern appears on 2 lines: one inside EXIV2_BUILD_SAMPLES for
        # bashTests, one for the 5 pytest suites).
        root_cm = os.path.join(self.source_folder, "CMakeLists.txt")
        replace_in_file(self, root_cm,
            "if (Python3_Interpreter_FOUND)",
            "if (FALSE AND Python3_Interpreter_FOUND)",
            strict=False)
        replace_in_file(self, root_cm,
            "if (Python3_Interpreter_FOUND)",
            "if (FALSE AND Python3_Interpreter_FOUND)",
            strict=False)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Remove static libtool .la and pkg-config files we do not ship
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "exiv2")
        self.cpp_info.set_property("cmake_target_name", "exiv2::exiv2")
        self.cpp_info.set_property("pkg_config_name", "exiv2")
        # The CMake target is named "exiv2lib" but has OUTPUT_NAME "exiv2",
        # so the artifact on disk is libexiv2.a → libs entry is "exiv2".
        self.cpp_info.libs = ["exiv2"]
        # exiv2 depends on expat and zlib (carried via Conan requires, but also
        # declare system libs for Linux-like platforms — R32)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl"]
        # The exiv2 command-line binary is installed to bin/
        self.cpp_info.bindirs = ["bin"]
