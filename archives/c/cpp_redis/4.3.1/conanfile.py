#!/usr/bin/env python3
"""Conan recipe — cpp_redis 4.3.1 (CMake).

Builds the static library with tacopie bundled from the same source tree.
Patches: install bin-dir guard (no RUNTIME output for static-only build) and
googletest ExternalProject mirror/tag for upstream tests (see notes.md).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CppredisConan(ConanFile):
    name = "cpp_redis"
    version = "4.3.1"
    description = "C++11 Asynchronous Multi-Platform Lightweight Redis Client"
    license = "MIT"
    homepage = "https://github.com/Cylix/cpp_redis"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # cpp_redis has no external dependency; tacopie is bundled in-tree
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # tacopie is a git submodule absent from the release tarball; fetch the
        # pinned commit (243089d) into tacopie/ so the in-tree build works.
        get(self, **self.conan_data["tacopie"], strip_root=True, destination="tacopie")

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Upstream requires CMake >= 2.8.7, unsupported by modern CMake
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
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
        # cpp_redis requires the in-tree tacopie static library at link time
        self.cpp_info.libs = ["cpp_redis", "tacopie"]
