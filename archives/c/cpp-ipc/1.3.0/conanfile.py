#!/usr/bin/env python3
"""Conan recipe — cpp-ipc 1.3.0 (CMake, C++17 shared-memory IPC library).

cpp-ipc is a header + static/shared C++17 library that implements
inter-process channels, queues, mutexes and waiters on top of POSIX shared
memory. It has no third-party dependencies: only the compiler, pthread and
the (empty on musl) librt stub are needed.

Upstream builds one library target called `ipc` (file name libipc) and
installs `include/libipc/*.h`; tests and demos are behind separate options
and are off here.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class CppipcConan(ConanFile):
    name = "cpp-ipc"
    version = "1.3.0"
    description = "High performance C++ inter-process communication library (shared memory, message queue, ring buffer)"
    license = "MIT"
    homepage = "https://github.com/mutouyun/cpp-ipc"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

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
        # E092: CMake has no HarmonyOS platform module, so tell CMake the
        # target is Linux (the kernel/ABI this library talks to).
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["LIBIPC_BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Upstream tests need the bundled googletest and are run separately;
        # the packaged library must stay dependency free.
        tc.variables["LIBIPC_BUILD_TESTS"] = "OFF"
        tc.variables["LIBIPC_BUILD_DEMOS"] = "OFF"
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
        self.cpp_info.libs = ["ipc"]
        # Upstream target links pthread and rt (both provided by the OHOS
        # sysroot; on musl librt is an empty stub).
        self.cpp_info.system_libs = ["pthread", "rt"]
