#!/usr/bin/env python3
"""Conan recipe — mikelankamp-fpm 1.1.0 (header-only C++ fixed-point math library).

Upstream project `fpm` ("fixed-point math") by Mike Lankamp: a CMake INTERFACE
target that ships three headers under `include/fpm/` and compiles no library
artifact of its own. Package type is `header-library` and `package_id()` is
cleared, so one package id serves every configuration.

OHOS adaptation notes (full detail in notes.md):

  * No patches are required. The v1.1.0 sources build and the whole upstream
    GoogleTest suite passes on the OHOS clang 15 toolchain unmodified, so
    `patches/` is intentionally absent for this version.

  * v1.1.0's `CMakeLists.txt` has **no option switches at all**: it
    unconditionally declares `ExternalProject_Add` clones of two comparison
    libraries (libfixmath, cnl) and builds `fpm-benchmark` / `fpm-accuracy`
    as part of the default `all` target. Building the default target would
    therefore need network access during `conan create`. build() instead
    configures the project and builds the **test target explicitly**
    (`fpm-test`), which depends only on the vendored `3rdparty/googletest`
    tree — no download, no benchmark/accuracy toolchain.

  * `build()` then executes `fpm-test` so the conan build itself proves the
    upstream suite passes under the exact toolchain CI uses. The counted
    results (test count / pass rate / the four counting methods) live in
    `test_package/MANIFEST.yml` and `notes.md`; they are never inferred from
    this recipe.

  * `package()` copies `include/fpm/*.hpp` with the `fpm/` prefix preserved
    so `#include <fpm/fixed.hpp>` keeps working for consumers, plus `LICENSE`
    under `licenses/`.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import (
    apply_conandata_patches, copy, export_conandata_patches, get,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class MikelankampFpmConan(ConanFile):
    name = "mikelankamp-fpm"
    version = "1.1.0"
    package_type = "header-library"

    description = ("fpm - C++ header-only fixed-point math library providing "
                   "fixed_16_16 / fixed_24_8 / fixed_8_24 drop-in floating "
                   "point replacements")
    homepage = "https://github.com/MikeLankamp/fpm"
    license = "MIT"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Required by the repository static gate (settings must be complete).
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Cap parallelism explicitly: Conan's CMake helper would otherwise pass
        # -j<os.cpu_count()> (20) while the device only has 8 CPUs in its
        # affinity mask, i.e. 2.5x oversubscription on a shared device.
        tc.generate()
        self.conf.define("tools.build:jobs", 2)

    def build(self):
        """Configure the upstream CMake project and build/run its test target.

        The default `all` target is deliberately not built: for v1.1.0 it
        drags in `ExternalProject_Add` git clones of two comparison libraries
        plus the benchmark/accuracy tools, none of which belong to the
        delivered package (and none of which may be fetched during a
        hermetic `conan create`).
        """
        cmake = CMake(self)
        cmake.configure()
        cmake.build(target="fpm-test")

        test_bin = os.path.join(self.build_folder, "fpm-test")
        if not os.path.isfile(test_bin):
            raise Exception(
                "fpm-test was not produced by the upstream build: %s" % test_bin)
        # Running the upstream suite here is the in-build proof that the
        # delivered headers work under the CI toolchain; a non-zero exit code
        # fails the recipe build instead of being silently swallowed.
        self.run('"%s"' % test_bin)

    def package_id(self):
        # Header-only: no build artifact depends on the configuration.
        self.info.clear()

    def package(self):
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "include", "fpm"),
             dst=os.path.join(self.package_folder, "include", "fpm"))
        copy(self, "LICENSE", self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        # No binaries and no linkable artifacts in a header-only package.
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # Upstream ships no CMake package config; export the natural names so
        # consumers can `find_package(fpm CONFIG)` and link `fpm::fpm`.
        self.cpp_info.set_property("cmake_file_name", "fpm")
        self.cpp_info.set_property("cmake_target_name", "fpm::fpm")
