#!/usr/bin/env python3
"""Conan recipe — erhling-clibs 2.1.1 (single-file C library collection).

Build system: CMake (CMakeLists.txt).  Upstream CMakeLists.txt defines
target `clibs` (libclibs) but has NO install() rules, so package() copies
the headers and the built static archive manually.
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class ErhlingclibsConan(ConanFile):
    name = "erhling-clibs"
    version = "2.1.1"
    description = "A collection of single-file C libraries (critbit trie, selist, strings, strutil, l10n, format)"
    license = "MIT"
    homepage = "https://github.com/ennorehling/clibs"
    url = ""  # CI fills this

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
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # Upstream has no install() rule; copy headers + built library manually.
        libext = ".so" if self.options.shared else ".a"
        libname = f"libclibs{libext}"
        src_lib = os.path.join(self.build_folder, libname)
        if not os.path.isfile(src_lib):
            src_lib = os.path.join(self.build_folder, "lib", libname)
        copy(self, libname, src=os.path.dirname(src_lib),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        for header in ("cmdline.h", "critbit.h", "format.h", "l10n.h",
                       "selist.h", "strings.h", "strutil.h"):
            copy(self, header, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "include"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["clibs"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "erhling-clibs")
        self.cpp_info.set_property("cmake_target_name", "erhling-clibs::erhling-clibs")
