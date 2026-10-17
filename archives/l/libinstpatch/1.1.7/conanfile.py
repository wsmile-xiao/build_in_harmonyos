#!/usr/bin/env python3
"""Conan recipe — libinstpatch 1.1.7 (CMake, glib + libsndfile).

Upstream build is CMake-only for 1.1.7 (no autotools files). It locates
glib/gobject/gthread and sndfile via pkg_check_modules, so dependencies are
exposed through PkgConfigDeps (pkg-config .pc generation).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class LibinstpatchConan(ConanFile):
    name = "libinstpatch"
    version = "1.1.7"
    description = "MIDI instrument patch library (DLS/SF2/Gig/RealFont/SLI)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/swami/libinstpatch"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.88.3.1")
        self.requires("libsndfile/1.2.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Upstream uses pkg_check_modules(REQUIRED gobject-2.0 glib-2.0 gthread-2.0)
        # and pkg_check_modules(SNDFILE REQUIRED sndfile>=1.2.1): expose deps as .pc.
        PkgConfigDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["GTKDOC_ENABLED"] = "OFF"
        tc.variables["INTROSPECTION_ENABLED"] = "OFF"
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
        # Installed artifact: lib/libinstpatch-1.0.so, headers in
        # include/libinstpatch-2/libinstpatch/<*.h>.
        self.cpp_info.libs = ["instpatch-1.0"]
        self.cpp_info.includedirs = ["include/libinstpatch-2"]
        self.cpp_info.set_property("cmake_file_name", "libinstpatch")
        self.cpp_info.set_property("cmake_target_name", "libinstpatch::libinstpatch")
        self.cpp_info.set_property("pkg_config_name", "libinstpatch-1.0")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]