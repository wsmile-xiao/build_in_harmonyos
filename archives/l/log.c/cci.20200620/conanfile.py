#!/usr/bin/env python3
"""Conan recipe for rxi/log.c cci.20200620."""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LogcConan(ConanFile):
    name = "log.c"
    version = "cci.20200620"
    description = "A simple logging library implemented in C99"
    license = "MIT"
    homepage = "https://github.com/rxi/log.c"
    url = "https://github.com/conan-io/conan-center-index"
    topics = ("logging", "log", "logging-library", "logc", "purec", "c99")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        ranlib = compilers.get("ranlib", "llvm-ranlib")
        source = os.path.join(self.source_folder, "src", "log.c")
        include = os.path.join(self.source_folder, "src")
        object_file = os.path.join(self.build_folder, "log.o")
        library = os.path.join(self.build_folder, "liblog.c.a")
        pic_flag = " -fPIC" if self.options.fPIC else ""

        self.run(
            f'"{cc}" -std=c99 -Wall -Wextra -Wpedantic{pic_flag} '
            f'-I"{include}" -c "{source}" -o "{object_file}"'
        )
        self.run(f'"{ar}" rcs "{library}" "{object_file}"')
        self.run(f'"{ranlib}" "{library}"')

    def package(self):
        copy(
            self,
            "log.h",
            src=os.path.join(self.source_folder, "src"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "liblog.c.a",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["log.c"]
        self.cpp_info.set_property("cmake_file_name", "log.c")
        self.cpp_info.set_property("cmake_target_name", "log.c::log.c")
        self.cpp_info.set_property("pkg_config_name", "log.c")
