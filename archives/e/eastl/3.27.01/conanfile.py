#!/usr/bin/env python3
"""Conan recipe for EASTL 3.27.01 (Electronic Arts Standard Template Library)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, export_conandata_patches, get, patch


class EastlConan(ConanFile):
    name = "eastl"
    version = "3.27.01"
    description = "Electronic Arts Standard Template Library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/electronicarts/EASTL"
    url = "https://github.com/electronicarts/EASTL"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # EASTL public headers include EABase headers, so propagate them to consumers.
        self.requires("eabase/0699a15", transitive_headers=True)

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        sources = self.conan_data["sources"]
        get(self, **sources["eastl"], strip_root=True)
        packages = os.path.join(self.source_folder, "test", "packages")
        eabase = os.path.join(packages, "EABase")
        os.makedirs(eabase, exist_ok=True)
        # Point upstream FetchContent at the patched Conan dependency rather
        # than downloading and rebuilding a second, unpatched EABase copy.
        with open(os.path.join(eabase, "CMakeLists.txt"), "w", encoding="utf-8") as cmake_file:
            cmake_file.write(
                "cmake_minimum_required(VERSION 3.5)\n"
                "project(EABase LANGUAGES CXX)\n"
                "add_library(EABase INTERFACE)\n"
                'target_include_directories(EABase INTERFACE "${EABASE_INCLUDE_DIR}")\n'
            )
        for package, source in sources["test_dependencies"].items():
            get(self, **source, filename=f"{package}.tar.gz", strip_root=True,
                destination=os.path.join(packages, package))
        for patch_data in self.conan_data.get("patches", []):
            patch_data = dict(patch_data)
            target = patch_data.pop("patch_target")
            base_path = (os.path.join(packages, "EAThread")
                         if target == "ea_thread_test_dependency" else self.source_folder)
            patch(self, patch_file=os.path.join(self.export_sources_folder,
                                                patch_data["patch_file"]),
                  base_path=base_path, strip=0)
        # EAThread calls several glibc pthread extensions missing from the
        # OHOS libc. This portability patch is confined to the upstream test
        # framework; EASTL production sources and runtime behavior are untouched.
    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["EASTL_BUILD_TESTS"] = True
        tc.variables["EASTL_BUILD_BENCHMARK"] = False
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        if self.settings.os == "OHOS":
            # The upstream ARM64 compiler probe advertises 128-bit integral
            # RMW operations that EASTL does not implement for this target.
            tc.preprocessor_definitions["EASTL_DISABLE_ATOMIC_128BIT"] = None
        # EASTL's test project uses FetchContent for its pinned EA test libraries.
        # Source archives are downloaded and checksum-verified in source().
        packages = os.path.join(self.source_folder, "test", "packages")
        for package in ("EABase", "EAAssert", "EAStdC", "EAMain", "EATest", "EAThread"):
            tc.variables[f"FETCHCONTENT_SOURCE_DIR_{package.upper()}"] = os.path.join(packages, package)
        tc.variables["EABASE_INCLUDE_DIR"] = os.path.join(
            self.dependencies["eabase"].package_folder, "include")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Conan's CMake.test() only builds the CMake "test" target; it does
        # not execute the registered tests. Run the official upstream CTest
        # entry explicitly after building EASTLTest.
        cmake.test()
        ctest_dir = os.path.join(self.build_folder, "test")
        self.run(f'ctest --test-dir "{ctest_dir}" --output-on-failure')

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Carry the official upstream test runner into the package so the
        # consumer test package can execute the same upstream test on target.
        copy(self, "EASTLTest", src=os.path.join(self.build_folder, "test"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["EASTL"]
        # Upstream CMake defines this for both EASTL and its tests; consumers
        # need the same public allocation ABI used by the built library.
        self.cpp_info.defines = ["EASTL_OPENSOURCE=1"]
        if self.settings.os == "OHOS":
            self.cpp_info.defines.append("EASTL_DISABLE_ATOMIC_128BIT")
        self.cpp_info.set_property("cmake_file_name", "eastl")
        self.cpp_info.set_property("cmake_target_name", "eastl::eastl")
        self.cpp_info.requires = ["eabase::eabase"]
