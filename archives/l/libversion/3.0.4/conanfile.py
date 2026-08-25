#!/usr/bin/env python3
"""Conan recipe — libversion 3.0.4 (CMake build).

libversion is an advanced version string comparison library by the Repology
project.  Pure C library (plus one C++ utility), no external dependencies,
built with CMake ≥ 3.22.1.

Upstream always builds BOTH a shared and a static target (OUTPUT_NAME=version
for both), plus CLI tools (version_compare, version_sort) linked against the
shared target.  libversion is NOT a system-name library (no libversion.so in
/lib or /lib64), so R26 does not apply and packaging is safe.

Products installed by upstream:
  - libversion.so / libversion.a      (-lversion, OUTPUT_NAME=version)
  - Headers: libversion/version.h, libversion/config.h, libversion/export.h
  - pkg-config: libversion.pc
  - CMake config: libversionConfig.cmake (removed in package() to avoid
    target conflicts with Conan's CMakeDeps)
  - CLI: version_compare, version_sort  (version_explain is NOT installed)
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rmdir
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibversionConan(ConanFile):
    name = "libversion"
    version = "3.0.4"
    description = "Advanced version string comparison library"
    license = "MIT"
    homepage = "https://github.com/repology/libversion"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Remove upstream CMake config files — they define
        # libversion::libversion and libversion::libversion_static targets
        # that would clash with the targets CMakeDeps generates from
        # cpp_info.
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        # Upstream always builds both shared and static; keep only the one
        # requested by the consumer.
        if self.options.shared:
            # Remove static library and its libtool file
            for f in glob.glob(os.path.join(self.package_folder, "lib", "*.a")):
                os.remove(f)
        else:
            # Remove shared library and symlinks
            for f in glob.glob(os.path.join(self.package_folder, "lib", "*.so*")):
                os.remove(f)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libversion")
        self.cpp_info.set_property("cmake_target_name", "libversion::libversion")
        self.cpp_info.set_property("pkg_config_name", "libversion")
        # OUTPUT_NAME=version in upstream CMake → libversion.so / libversion.a
        self.cpp_info.libs = ["version"]
        # When consuming the static build, LIBVERSION_STATIC_DEFINE must be
        # defined so that LIBVERSION_EXPORT resolves to empty (via the
        # generate_export_header mechanism).
        if not self.options.shared:
            self.cpp_info.defines = ["LIBVERSION_STATIC_DEFINE"]
        self.cpp_info.bindirs = ["bin"]
