#!/usr/bin/env python3
"""Conan recipe for libgd 2.3.3.2, the GD Graphics Library."""

import os
import re

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import collect_libs, get


class LibGdConan(ConanFile):
    name = "gd"
    version = "2.3.3.2"
    description = "GD Graphics Library for dynamic image creation"
    license = "BSD-like"
    homepage = "https://libgd.github.io/"
    url = "https://github.com/libgd/libgd"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_upstream_tests": [True, False],
    }
    default_options = {"shared": False, "fPIC": True, "with_upstream_tests": False}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_STATIC_LIBS"] = "OFF" if self.options.shared else "ON"
        tc.variables["BUILD_TEST"] = "ON" if self.options.with_upstream_tests else "OFF"
        tc.variables["ENABLE_AVIF"] = "OFF"
        tc.variables["ENABLE_CPP"] = "OFF"
        tc.variables["ENABLE_FONTCONFIG"] = "OFF"
        tc.variables["ENABLE_FREETYPE"] = "OFF"
        tc.variables["ENABLE_GD_FORMATS"] = "OFF"
        tc.variables["ENABLE_HEIF"] = "OFF"
        tc.variables["ENABLE_ICONV"] = "OFF"
        tc.variables["ENABLE_JPEG"] = "OFF"
        tc.variables["ENABLE_LIQ"] = "OFF"
        tc.variables["ENABLE_PNG"] = "OFF"
        tc.variables["ENABLE_RAQM"] = "OFF"
        tc.variables["ENABLE_TIFF"] = "OFF"
        tc.variables["ENABLE_WEBP"] = "OFF"
        tc.variables["ENABLE_XPM"] = "OFF"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.generate()

    def build(self):
        if self.options.with_upstream_tests:
            self._prepare_upstream_tests()
        self._disable_unneeded_subdirs(
            disable_test_targets=not self.options.with_upstream_tests,
        )
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.with_upstream_tests and can_run(self):
            cmake.test()

    def package(self):
        CMake(self).install()

    def package_info(self):
        libs = collect_libs(self)
        self.cpp_info.libs = libs or ["gd"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "gd")
        self.cpp_info.set_property("cmake_target_name", "gd::gd")
        self.cpp_info.set_property("pkg_config_name", "gdlib")
        if self.settings.os == "Windows" and not self.options.shared:
            self.cpp_info.defines.extend(["BGDWIN32", "NONDLL"])
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]

    def _prepare_upstream_tests(self):
        missing_test_entries = (
            ("tests/CMakeLists.txt", "gdmatrix"),
            ("tests/gdimagecopyrotated/CMakeLists.txt", "bug00320"),
            ("tests/gif/CMakeLists.txt", "bug00415"),
        )
        for relative_path, entry in missing_test_entries:
            cmake_path = os.path.join(self.source_folder, *relative_path.split("/"))
            with open(cmake_path, encoding="utf-8") as source:
                content = source.read()
            # These entries are listed by CMake but omitted from the 2.3.3 release archive.
            content = self._comment_out_cmake_line(content, entry, "missing release test source")
            with open(cmake_path, "w", encoding="utf-8") as target:
                target.write(content)

        root_cmake = os.path.join(self.source_folder, "CMakeLists.txt")
        with open(root_cmake, encoding="utf-8") as source:
            content = source.read()
        marker = 'SET(GD_LIB_STATIC "${GD_LIB}_static")'
        replacement = f'''{marker}

# Static-only builds do not create the upstream gd target. Point test helpers
# at the existing gd_static CMake target so it is built before they link.
if (NOT BUILD_SHARED_LIBS AND BUILD_STATIC_LIBS)
    SET(GD_LIB ${{GD_LIB_STATIC}})
endif()'''
        if marker not in content:
            raise RuntimeError("libgd static test target marker not found")
        with open(root_cmake, "w", encoding="utf-8") as target:
            target.write(content.replace(marker, replacement, 1))

    def _disable_unneeded_subdirs(self, disable_test_targets):
        cmake_lists = os.path.join(self.source_folder, "CMakeLists.txt")
        with open(cmake_lists, encoding="utf-8") as source:
            content = source.read()
        if disable_test_targets:
            content = self._comment_out_cmake_line(content, "add_subdirectory(tests)", "tests")
            content = self._comment_out_cmake_line(content, "add_subdirectory(examples)", "examples")
        content = self._comment_out_cmake_line(content, "add_subdirectory(docs)", "docs")
        with open(cmake_lists, "w", encoding="utf-8") as target:
            target.write(content)

        src_cmake = os.path.join(self.source_folder, "src", "CMakeLists.txt")
        with open(src_cmake, encoding="utf-8") as source:
            src_content = source.read()
        src_content = re.sub(
            r"^(\s*)set\(GD_PROGRAMS\s+gdcmpgif\)\s*$",
            r"\1set(GD_PROGRAMS)",
            src_content,
            flags=re.MULTILINE,
        )
        src_content = self._comment_out_cmake_line(
            src_content,
            "install(PROGRAMS bdftogd DESTINATION bin)",
            "bdftogd install",
        )
        with open(src_cmake, "w", encoding="utf-8") as target:
            target.write(src_content)

    @staticmethod
    def _comment_out_cmake_line(content, statement, label):
        pattern = r"^(\s*)" + re.escape(statement) + r"\s*$"
        return re.sub(
            pattern,
            lambda match: f"{match.group(1)}# {label} disabled by Conan recipe",
            content,
            flags=re.MULTILINE,
        )
