#!/usr/bin/env python3
"""Conan recipe — tacopie 3.1.0 (CMake).

tacopie is a multi-platform TCP Client & Server C++11 library with **no
dependency** (its only requirement is C++11). The upstream CMakeLists.txt
glob-compiles sources/{network,utils} plus the unix/ or windows/ socket
implementation and installs include/, lib/ and bin/ via install(DIRECTORY).

HarmonyOS notes:
- Upstream targets pthread on non-Windows; OHOS libc provides pthread
  symbols, so `pthread` is passed as a system lib for consumers.
- Upstream declares cmake_minimum_required(2.8.7); CMake 4.x rejects
  policies older than 3.5, so CMAKE_POLICY_VERSION_MINIMUM=3.5 is set.
- The upstream test suite requires googletest via ExternalProject (git
  clone) and the official 3.1.0 tag ships only tests/sources/main.cpp (a
  gtest runner with no spec sources), so BUILD_TESTS is kept OFF in the
  published package; correctness is verified by the packed test_package
  consumer (tcp_server/tcp_client round-trip on OHOS).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class TacopieConan(ConanFile):
    name = "tacopie"
    version = "3.1.0"
    description = "Multi-platform TCP Client & Server C++11 library"
    license = "MIT"
    homepage = "https://github.com/Cylix/tacopie"
    url = ""  # CI fills this
    topics = ("tcp", "client", "server", "network", "cpp11")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream honors BUILD_SHARED_LIBS (CHANGELOG 3.1.0: removed
        # explicit STATIC from add_library so dynamic builds work).
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Tests/examples are not part of the published package.
        tc.variables["BUILD_TESTS"] = "OFF"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        # Upstream cmake_minimum_required(2.8.7) vs CMake 4.x.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
        self.cpp_info.libs = ["tacopie"]
        if self.settings.os != "Windows":
            self.cpp_info.system_libs = ["pthread"]
