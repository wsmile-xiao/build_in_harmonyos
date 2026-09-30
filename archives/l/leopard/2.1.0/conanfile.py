#!/usr/bin/env python3
"""Conan recipe — leopard 2.1.0 (header-only C++ thread pool, C++20).

Leopard is a light-weight C++ thread pool with global/local queues and a
work-stealing scheduler (`hmthrp::ThreadPool`, `hmthrp::SharedQueue`).  It is
header-only: the package contains `include/Leopard/*.{h,tcc}` plus the licence.
There are no third-party Conan dependencies (only C++20 + pthread).

Upstream CMake at tag 2.1.0 is incomplete and needs patch 0001 (see
`patches/`): no target is ever declared, so `install(EXPORT ThreadPoolExport)`
stops configure with "INSTALL(EXPORT) given unknown export"; `test/` includes
`<Leopard/...>` but no include path is configured; the install rule still
names the pre-rename `include/ThreadPool` directory; and C++20 is never
selected although the headers use concepts/`std::optional`.

The upstream test suite (`test/CMakeLists.txt`, 7 `add_test` entries) is built
and executed by `build()` through `cmake.test()`.  The suite's only oracles are
`assert()` expressions, so the build must not define `NDEBUG`: CMake's default
`CMAKE_CXX_FLAGS_RELEASE` carries `-DNDEBUG`, which compiles every assertion
away and turns `test/par_sort_tester.cc`'s orderedness check (a `for` loop whose
*only* increment lives inside `assert(...)`) into an infinite loop.  The
recipe therefore pins the release flags back to `-O3`.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
import os


class LeopardConan(ConanFile):
    name = "leopard"
    version = "2.1.0"
    description = "C++ light-weight thread pool library with work stealing (header-only)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/hosseinmoein/Leopard"
    url = "https://github.com/hosseinmoein/Leopard"
    topics = ("threadpool", "concurrency", "async", "work-stealing", "header-only")
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # The headers are C++20 (concepts + std::optional).  The CI profile pins
        # compiler.cppstd=17, so raise it here; package_id is cleared below, so
        # this does not fragment the package id.
        if self.settings.compiler.get_safe("cppstd"):
            self.settings.compiler.cppstd = "20"

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 20)
        elif self.settings.compiler not in ("clang", "gcc", "apple-clang", "msvc"):
            raise ConanInvalidConfiguration("leopard requires a C++20 compiler")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["HMTHRP_TESTING"] = True
        # Keep assert() oracles alive: see the module docstring.
        if str(self.settings.build_type) == "Release":
            tc.cache_variables["CMAKE_CXX_FLAGS_RELEASE"] = "-O3"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Runs the 7 upstream ctest entries (7 programs, 16 named sub-tests).
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "License", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        # Header-only: one package id regardless of os/compiler/arch/build_type.
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "ThreadPool")
        self.cpp_info.set_property("cmake_target_name", "ThreadPool::ThreadPool")
        self.cpp_info.set_property("pkg_config_name", "ThreadPool")
        if self.settings.os in ("Linux", "FreeBSD", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
