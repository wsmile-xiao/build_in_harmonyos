#!/usr/bin/env python3
"""Conan recipe for naive-tsearch 0.1.1 (CMake, static library + header-only).

naive-tsearch is a portable C99 implementation of the POSIX tsearch() family
(tsearch/tfind/tdelete/twalk/tdestroy) for platforms whose libc lacks it.
Upstream ships a CMake build with an optional Boost.Test suite under tests/
that exercises three implementations: the compiled static library, the
header-only flavour (NAIVE_TSEARCH_HDRONLY), and the system <search.h>.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)


class NaiveTsearchConan(ConanFile):
    name = "naive-tsearch"
    version = "0.1.1"
    description = "A simple tsearch() implementation for platforms without one"
    license = "MIT"
    homepage = "https://github.com/kulp/naive-tsearch"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("tsearch", "tfind", "tdelete", "twalk", "binary-search-tree")
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # tests/CMakeLists.txt does find_package(Boost REQUIRED COMPONENTS
        # unit_test_framework); test_requires keeps Boost out of the consumer
        # graph while still letting build() compile and run the suite.
        self.test_requires("boost/1.90.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # Upstream defaults these to ON only for the top-level project; set
        # them explicitly so the recipe always builds the install tree and
        # the Boost.Test suite (3 ctest cases).
        tc.cache_variables["NAIVE_TSEARCH_TESTS"] = True
        tc.cache_variables["NAIVE_TSEARCH_INSTALL"] = True
        # The suite links the compiled Boost.Test library (the ohpcd boost
        # binary is shared=False); upstream only defines BOOST_TEST_DYN_LINK
        # when this variable is falsy.
        tc.cache_variables["Boost_USE_STATIC_LIBS"] = True
        # CMakeDeps injects -DBOOST_TEST_DYN_LINK=0 for the static Boost.Test
        # package, and unit_test.hpp reacts to *defined(BOOST_TEST_DYN_LINK)*
        # (value-insensitive): tests/main.cpp would emit a second main while
        # libboost_unit_test_framework.a already carries unit_test_main.o —
        # which hosts both the archive's main and the required
        # unit_test_main() function ("duplicate symbol: main", device 2026-09-
        # 25). BOOST_TEST_NO_MAIN keeps the archive main and links it against
        # the init_unit_test() that BOOST_TEST_MODULE generates in main.cpp.
        tc.extra_cxxflags = ["-DBOOST_TEST_NO_MAIN"]
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Run the upstream suite in-build so `conan create` (W3/CI) executes
        # all 3 ctest cases: naive static / header-only / system tsearch.
        self.run(
            "ctest --output-on-failure -C {}".format(str(self.settings.build_type)),
            cwd=self.build_folder,
            env="conanbuild",
        )

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()
        # Keep the installed headers of both flavours (public headers plus
        # tsearch_hdronly.h/tsearch.c.inc for the header-only mode) and the
        # static library; drop the duplicated share/ license, upstream's own
        # CMake export tree and .pc file — CMakeDeps/pkg-config metadata from
        # package_info() supersede them for Conan consumers.
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "naive-tsearch")
        self.cpp_info.set_property("cmake_target_name", "naive-tsearch::naive-tsearch")
        self.cpp_info.set_property("pkg_config_name", "naive-tsearch")
        self.cpp_info.libs = ["naive-tsearch"]
        # Headers install to include/naive-tsearch/; expose both roots so
        # consumers can use `#include <search.h>` (upstream's .pc Cflags) or
        # `#include <naive-tsearch/search.h>`.
        self.cpp_info.includedirs.append(os.path.join("include", "naive-tsearch"))
