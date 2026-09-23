#!/usr/bin/env python3
"""Conan recipe — EAMain 0.0.0-24ca8bf (Electronic Arts entry point / main library).

EAMain supplies a cross-platform main entry point, command-line parsing,
report/print facilities and platform startup/shutdown for EA applications.
Upstream is a CMake project (project(EAMain CXX)); the release tarball does
not include the test/packages submodules, so the CommonCppFlags include is
removed by patch 0001 and tests are built by this recipe's own test_package.

OHOS adaptation:
  - CMake build with the OHOS Conan toolchain (clang 15, aarch64-linux-ohos).
  - Depends on the EA base libraries already adapted for OHOS:
    eabase (header-only, published), eaassert, eastdc, eathread.
  - Static library (BUILD_SHARED_LIBS=OFF) per R26.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.scm import Version
import os


class EamainConan(ConanFile):
    name = "eamain"
    version = "0.0.0-24ca8bf"
    description = "EAMain - Electronic Arts cross-platform main entry point and command line parser"
    license = "BSD-3-Clause"
    homepage = "https://github.com/electronicarts/EAMain"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    generators = "CMakeDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("eabase/0699a15")
        self.requires("eaassert/0.0.0-e5e1812")
        self.requires("eastdc/0.0.0-fbcc34e")
        self.requires("eathread/0.0.0-f3c6c54")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: static by default
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # The upstream tarball omits test/packages submodules; upstream tests
        # are covered by this recipe's test_package consumer instead.
        tc.variables["EAMAIN_BUILD_TESTS"] = "OFF"
        # Upstream CMakeLists compiles sources that include EABase/EAAssert/
        # EAStdC/EAThread headers but has no CMake targets to propagate them,
        # so inject the installed dependencies' include dirs (same approach as
        # the eastdc/0.0.0-fbcc34e recipe).
        inc_flags = []
        for dep_name in ("eabase", "eaassert", "eastdc", "eathread"):
            dep = self.dependencies[dep_name]
            pkg = dep.package_folder
            for inc in dep.cpp_info.includedirs:
                inc_flags.append(f"-I{os.path.join(pkg, inc)}")
        if inc_flags:
            tc.variables["CMAKE_CXX_FLAGS"] = " ".join(inc_flags)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream CMakeLists has no install rules; ship headers and library
        # explicitly so the package is self-contained.
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.inl", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.a", src=os.path.join(self.build_folder),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.so", src=os.path.join(self.build_folder),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "EAMain")
        self.cpp_info.set_property("cmake_target_name", "EAMain::EAMain")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["EAMain"]
        # EAMain public headers unconditionally include EABase/EAAssert/EAStdC/
        # EAThread headers, so consumers must receive those packages' include
        # dirs too (full chain propagation, same as eastdc recipe).
        self.cpp_info.requires = ["eabase::eabase", "eaassert::eaassert",
                                  "eastdc::eastdc", "eathread::eathread"]
