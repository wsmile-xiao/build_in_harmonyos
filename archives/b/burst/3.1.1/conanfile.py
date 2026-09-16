#!/usr/bin/env python3
"""Conan recipe for Burst 3.1.1, a Boost-compatible header-only C++ library."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)


class BurstConan(ConanFile):
    name = "burst"
    version = "3.1.1"
    description = "Radix sort, lazy ranges and iterators, and other Boost-like utilities"
    license = "BSL-1.0"
    homepage = "https://github.com/izvolov/burst"
    url = "https://github.com/izvolov/burst"
    topics = ("algorithms", "ranges", "iterators", "header-only")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Public Burst headers use Boost.Range/Iterator/Asio APIs.
        self.requires("boost/1.90.0", transitive_headers=True)

    def build_requirements(self):
        # Only the upstream test suite needs doctest.
        self.test_requires("doctest/2.5.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # The repository Boost package intentionally ships Boost.System as
        # header-only and therefore has no Boost::system component. Burst's
        # upstream tests still request that historical target. Add a CMakeDeps
        # build module to the generated Boost config; this is the config Conan's
        # toolchain actually selects and avoids patching either upstream recipe.
        boost_system_module = '''\
if(NOT TARGET Boost::system)
    add_library(Boost::system INTERFACE IMPORTED)
    set_target_properties(Boost::system PROPERTIES
        INTERFACE_LINK_LIBRARIES Boost::boost)
endif()
'''
        module_path = os.path.join(self.generators_folder, "Boost-system.cmake")
        save(self, module_path, boost_system_module)
        deps = CMakeDeps(self)
        deps.set_property("boost", "cmake_build_modules", [module_path])
        deps.generate()

        tc = CMakeToolchain(self)
        tc.cache_variables["BURST_TESTING"] = True
        tc.cache_variables["BURST_BENCHMARKING"] = False
        tc.cache_variables["BURST_COVERAGE"] = False
        if str(self.settings.os) == "OHOS":
            # Burst is platform-neutral/POSIX-only. CMake has no built-in OHOS
            # platform module on every repository runner, so use the established
            # Linux platform model while retaining the OHOS compiler/profile.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            # AArch64 OHOS defaults plain `char` to unsigned, while Burst's
            # unchanged to_unsigned<char> test lists `char` as a signed type.
            # Match the upstream test model without patching or skipping it.
            tc.extra_cxxflags.append("-fsigned-char")
        if str(self.settings.compiler) in ("clang", "apple-clang"):
            # The repository profiles use C++17, while Burst 3.1.1 predates
            # std::result_of_t deprecation. Upstream promotes all warnings to
            # errors, so keep its tests strict except for this compatibility
            # diagnostic.
            tc.extra_cxxflags.append("-Wno-deprecated-declarations")
        if str(self.settings.compiler) == "apple-clang":
            # Apple Clang 17 also diagnoses u8-prefixed static_assert messages.
            tc.extra_cxxflags.append("-Wno-invalid-unevaluated-string")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # CMAKE_SYSTEM_NAME=Linux deliberately puts CMake in cross-compiling
        # mode on OHOS. In that mode upstream's custom `check` target leaves
        # `COMMAND burst-unit-tests` as a bare command, which is not found from
        # its working directory. Build the exact upstream test executable and
        # run it by absolute path with the same arguments as the `check` target.
        # This executes all 724 doctest cases; it does not skip or replace them.
        cmake.build(target="burst-unit-tests")
        test_binary = os.path.join(self.build_folder, "test", "burst-unit-tests")
        self.run(
            f'"{test_binary}" --report_level=short --color_output',
            env="conanrun",
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = ["boost::boost"]
        self.cpp_info.set_property("cmake_file_name", "Burst")
        self.cpp_info.set_property("cmake_target_name", "Burst::burst")

    def package_id(self):
        self.info.clear()
