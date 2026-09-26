#!/usr/bin/env python3
"""Conan recipe - serialize 1.4.4 (single-header bitpacking serializer).

serialize is Glenn Fiedler / Mas Bandwidth LLC's single-header C++ bitpacking
serializer (serialize.h, ~3.2k lines). Upstream is a standard CMake project
that exposes an INTERFACE target `serialize` (alias `serialize::serialize`) and
installs include/serialize.h plus lib/cmake/serialize/serialize-config.cmake.

Header-only: no compiled library, but upstream ships a real test suite
(test.cpp, 17 SERIALIZE_RUN_TEST functions registered as a single CTest case).
This recipe keeps the upstream test entry point alive in build() via
cmake.test() (TEST_QUALITY_SPEC layer 1) and installs through the upstream CMake
rules; test_package exercises the public API from the consumer side (R34/R51).
"""
from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class SerializeConan(ConanFile):
    name = 'serialize'
    version = '1.4.4'
    description = 'A simple bitpacking serializer for C++ (single header)'
    license = 'BSD-3-Clause'
    homepage = 'https://github.com/mas-bandwidth/serialize'
    url = ''  # CI fills this
    topics = ('serialization', 'bitpacking', 'header-only', 'network')

    package_type = 'header-library'
    settings = 'os', 'compiler', 'build_type', 'arch'

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Official GitHub archive (tag v1.4.4) extracts to serialize-1.4.4/;
        # strip_root collapses it. SHA-256 verified in conandata.yml (R39).
        get(self, **self.conan_data['sources'], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R32: treat OHOS in the Linux family with an explicit target triple.
        if self.settings.os in ('Linux', 'OHOS'):
            tc.cache_variables['CMAKE_SYSTEM_NAME'] = 'Linux'
            tc.cache_variables['CMAKE_SYSTEM_PROCESSOR'] = 'aarch64'
        # Layer 1 upstream tests: keep the upstream CTest entry point enabled.
        tc.cache_variables['SERIALIZE_BUILD_TESTS'] = True
        tc.cache_variables['SERIALIZE_INSTALL'] = True
        tc.cache_variables['SERIALIZE_FUZZ'] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream suite (test.cpp -> bin/test, one CTest case). Under a
        # cross-compile the freshly built OHOS aarch64 binaries cannot run on
        # the build machine, so execution is deferred to the target platform
        # (OHOS runtime evidence is captured in notes.md / MANIFEST.yml).
        if not cross_building(self):
            cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Mirror the upstream CMake package: find_package(serialize) + serialize::serialize
        self.cpp_info.set_property('cmake_file_name', 'serialize')
        self.cpp_info.set_property('cmake_target_name', 'serialize::serialize')
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
