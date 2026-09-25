#!/usr/bin/env python3
"""Conan recipe for libyajl 2.1.0 — Yet Another JSON Library (C).

Task #13878 (name `libyajl`, ecosystem package name distinct from the
pre-existing `yajl` archive). Pure C JSON parser/generator, zero runtime
dependencies (W0 verified).

yajl's CMake builds both a shared (libyajl.so) and a static (libyajl_s.a)
library unconditionally; the Conan `shared` option selects which artifact is
exported via cpp_info so consumers link the correct one.

yajl is NOT a system-name library (R26 does not require forced static
linking); the default dynamic library is managed by Conan's dependency chain.

Patches fix CMake 4.x incompatibility: the GET_TARGET_PROPERTY(... LOCATION)
pattern was removed in CMake 4.x; replaced with the $<TARGET_FILE:target>
generator expression.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibYajlConan(ConanFile):
    name = "libyajl"
    version = "2.1.0"
    description = "Yet Another JSON Library - C library for JSON parsing and generation"
    license = "ISC"
    homepage = "https://lloyd.github.io/yajl/"
    url = "https://github.com/lloyd/yajl"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Pure C library with no runtime dependencies (W0 confirmed).
        pass

    def validate(self):
        # R32: settings.os must be checked with "in", not "==".
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos"):
            raise ConanInvalidConfiguration(
                f"libyajl is only supported on Linux/OHOS/FreeBSD/Macos, not {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 4.x dropped compatibility with CMake < 3.5; yajl's top-level
        # CMakeLists.txt declares CMAKE_MINIMUM_REQUIRED(VERSION 2.6), which
        # CMake 4.x rejects. Must be a cache variable so it takes effect
        # before cmake_minimum_required() is evaluated.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # CMake 4.1.2 ships no Platform/HarmonyOS.cmake module, so
        # CMAKE_SHARED_LIBRARY_SONAME_C_FLAG is never set (unlike
        # Platform/Linux.cmake which defines "-Wl,-soname,"). Without it,
        # libyajl.so is linked with no SONAME field. yajl's src/CMakeLists.txt
        # sets SOVERSION ${YAJL_MAJOR} => TARGET_SONAME = libyajl.so.2; we
        # only need to supply the flag CMake would inherit from the platform
        # module.
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # Package the upstream yajl_test binary (built by
        # test/parsing/CMakeLists.txt) so test_package can run the 58 upstream
        # regression cases. yajl_test is NOT installed by `cmake --install`,
        # so locate it under the cmake build folder (search both single-config
        # in-place and cmake_layout build/<config>/ shapes).
        yajl_test_candidates = [
            os.path.join(self.build_folder, "test", "parsing", "yajl_test"),
            os.path.join(self.build_folder, "*", "test", "parsing", "yajl_test"),
        ]
        yajl_test_path = next(
            (p for pat in yajl_test_candidates for p in glob.glob(pat)
             if os.path.isfile(p)), None)
        if yajl_test_path:
            copy(self, "yajl_test", src=os.path.dirname(yajl_test_path),
                 dst=os.path.join(self.package_folder, "bin"))

        # Package the upstream test/parsing/cases/ data (*.json inputs +
        # *.json.gold expected outputs) consumed by yajl_test.
        cases_src = os.path.join(self.source_folder, "test", "parsing", "cases")
        copy(self, "*.json", src=cases_src, dst=os.path.join(self.package_folder, "test", "cases"))
        copy(self, "*.json.gold", src=cases_src, dst=os.path.join(self.package_folder, "test", "cases"))

    def package_info(self):
        # yajl's CMake installs both libyajl.so (shared) and libyajl_s.a
        # (static); export the library matching the `shared` option.
        if self.options.shared:
            self.cpp_info.libs = ["yajl"]
        else:
            self.cpp_info.libs = ["yajl_s"]
        # yajl also installs executables json_verify / json_reformat.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "yajl")
        self.cpp_info.set_property("pkg_config_name", "yajl")
