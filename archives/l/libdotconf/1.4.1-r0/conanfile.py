#!/usr/bin/env python3
"""Conan recipe for libdotconf 1.4.1-r0."""

import os

from conan import ConanFile
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibdotconfConan(ConanFile):
    name = "libdotconf"
    version = "1.4.1-r0"
    description = "Configuration file parser library"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/williamh/dotconf"
    url = homepage

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # The tag archive only contains configure.ac. Building the library source
        # directly avoids requiring aclocal/automake on the constrained CI worker.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        tool_dir = os.path.dirname(cc)
        ar = compilers.get("ar") or (
            os.path.join(tool_dir, "llvm-ar") if tool_dir else "llvm-ar"
        )
        ranlib = compilers.get("ranlib") or (
            os.path.join(tool_dir, "llvm-ranlib") if tool_dir else "llvm-ranlib"
        )

        source = os.path.join(self.source_folder, "src", "dotconf.c")
        include_dir = os.path.join(self.source_folder, "src")
        obj = os.path.join(self.build_folder, "dotconf.o")
        library = os.path.join(self.build_folder, "libdotconf.a")

        self.run(
            f'"{cc}" -std=c99 -D_GNU_SOURCE -O2 -fPIC -Wall '
            f'-I"{include_dir}" -c "{source}" -o "{obj}"'
        )
        self.run(f'"{ar}" rcs "{library}" "{obj}"')
        self.run(f'"{ranlib}" "{library}"')

    def package(self):
        copy(
            self,
            "dotconf.h",
            src=os.path.join(self.source_folder, "src"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "libdotconf.a",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["dotconf"]
        self.cpp_info.set_property("cmake_file_name", "libdotconf")
        self.cpp_info.set_property("cmake_target_name", "libdotconf::libdotconf")
        self.cpp_info.set_property("pkg_config_name", "dotconf")
