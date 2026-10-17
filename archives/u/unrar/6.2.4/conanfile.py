#!/usr/bin/env python3
"""Conan recipe — unrar 6.2.4 (makefile): UnRAR utility and libunrar library."""

import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class UnrarConan(ConanFile):
    name = "unrar"
    version = "6.2.4"
    description = "UnRAR utility and library for extracting RAR archives"
    license = "unrar"
    homepage = "https://www.rarlab.com/rar_add.htm"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        cxx = "clang++"
        strip = "llvm-strip"
        ar = "llvm-ar"

        src = self.source_folder

        self.run(f"make lib CXX={cxx} STRIP={strip} AR={ar} -j1", cwd=src)

        lib_dir = os.path.join(self.build_folder, "saved_libs")
        os.makedirs(lib_dir, exist_ok=True)
        for f in ["libunrar.a", "libunrar.so"]:
            src_file = os.path.join(src, f)
            if os.path.exists(src_file):
                copy(self, f, src, lib_dir)

        self.run(f"make CXX={cxx} STRIP={strip} AR={ar} -j1", cwd=src)

        bin_dir = os.path.join(self.build_folder, "saved_bin")
        os.makedirs(bin_dir, exist_ok=True)
        unrar_bin = os.path.join(src, "unrar")
        if os.path.exists(unrar_bin):
            copy(self, "unrar", src, bin_dir)

    def package(self):
        copy(self, "dll.hpp", self.source_folder, os.path.join(self.package_folder, "include"))

        lib_dir = os.path.join(self.build_folder, "saved_libs")
        if self.options.shared:
            copy(self, "libunrar.so", lib_dir, os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libunrar.a", lib_dir, os.path.join(self.package_folder, "lib"))

        bin_dir = os.path.join(self.build_folder, "saved_bin")
        copy(self, "unrar", bin_dir, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["unrar"]
        self.cpp_info.bindirs = ["bin"]
        if self.options.shared:
            self.cpp_info.defines.append("UNRAR_DLL")
