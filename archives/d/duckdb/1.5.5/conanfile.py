#!/usr/bin/env python3
"""Conan recipe for DuckDB 1.5.5 — CMake + Ninja build system.

DuckDB is an in-process analytical database.  It bundles all third-party
dependencies (fmt, pg_query, re2, miniz, utf8proc, zstd, parquet, ...) so no
external Conan requires are needed — re-verified for 1.5.5:
`third_party/` still carries the sources and the default extension set
(core_functions + parquet) is entirely in-tree, so no FetchContent download
happens during configure.

Key build notes for HarmonyOS (OHOS / aarch64):
  - Use Ninja generator (Unix Makefiles has try-compile detection issues).
    Ninja is also required because /bin/sh is not usable from the default
    Makefiles generator on the OHOS container.
  - Set CMAKE_BUILD_WITH_INSTALL_RPATH=ON for proper RPATH handling.
  - ** DUCKDB_EXPLICIT_PLATFORM is mandatory when cross-building. **
    Without it, CMakeLists.txt:873-887 adds an executable
    `duckdb_platform_binary` and a custom command that RUNS it to detect the
    target platform.  That binary is aarch64 and cannot execute on the build
    host, so a plain cross build fails.  Setting DUCKDB_EXPLICIT_PLATFORM
    takes the else() branch (CMakeLists.txt:888-895), which merely echoes the
    value, and additionally defines DUCKDB_CUSTOM_PLATFORM which short-
    circuits the legacy-C++-ABI #error in
    src/include/duckdb/common/platform.hpp:38-39.
  - Git history is absent in the tarball -> dummy version (v0.0.1), harmless.

Upstream install layout (verified against 1.5.5 CMake rules):
  include/duckdb.h, include/duckdb.hpp, include/duckdb_extension.h
  include/duckdb/**/*.hpp
  lib/libduckdb.so        (target `duckdb`, always built)
  lib/libduckdb_static.a  (target `duckdb_static`, always built)
  lib/cmake/DuckDB/DuckDBConfig.cmake
  bin/duckdb              (only when BUILD_SHELL=ON — disabled here)

Both the shared and the static library are unconditional in 1.5.5's
src/CMakeLists.txt (lines 96 and 107) — there is no shared/static switch —
so the recipe exposes no `shared` option and installs both.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class DuckdbConan(ConanFile):
    name = "duckdb"
    version = "1.5.5"
    description = "DuckDB is an in-process SQL OLAP database management system"
    license = "MIT"
    homepage = "https://duckdb.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # DuckDB 1.5.5 builds libduckdb.so and libduckdb_static.a unconditionally
    # (src/CMakeLists.txt:96,107) — there is no shared/static switch — so the
    # recipe declares no `shared` option.  Conan rejects
    # package_type="library" without that option ("Package type is 'library',
    # but no 'shared' option declared"), hence the static-library type.
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # all deps bundled (re-verified for 1.5.5)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generator = "Ninja"
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
        # Cross-build safety: never run duckdb_platform_binary (see module docstring).
        tc.variables["DUCKDB_EXPLICIT_PLATFORM"] = "linux_arm64"
        # Library-only package: no shell CLI, no unit test runner.
        # Extension support stays ON (linked statically); only the expensive
        # loadable-extension artifacts (which need the platform probe target
        # on the default `all` path) are skipped.
        tc.variables["BUILD_SHELL"] = False
        tc.variables["BUILD_UNITTESTS"] = False
        tc.variables["BUILD_BENCHMARKS"] = False
        tc.variables["EXTENSION_STATIC_BUILD"] = False
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
        self.cpp_info.libs = ["duckdb"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl", "m"]
