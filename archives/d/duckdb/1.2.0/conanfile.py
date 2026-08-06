#!/usr/bin/env python3
"""Conan recipe for DuckDB 1.2.0 — CMake + Ninja build system.

DuckDB is an in-process analytical database. It bundles all third-party
dependencies (fmt, pg_query, re2, miniz, utf8proc, etc.) so no external
Conan requires are needed.

Key build notes for HarmonyOS:
  - Use Ninja generator (Unix Makefiles has try-compile detection issues)
  - Set CMAKE_BUILD_WITH_INSTALL_RPATH=ON for proper RPATH handling
  - Git history absent in tarball -> dummy version (v0.0.1), harmless
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class DuckdbConan(ConanFile):
    name = "duckdb"
    version = "1.2.0"
    description = "DuckDB is an in-process SQL OLAP database management system"
    license = "MIT"
    homepage = "https://duckdb.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # all deps bundled

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.generator = "Ninja"
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.generator = "Ninja"
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["duckdb"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl", "m"]
