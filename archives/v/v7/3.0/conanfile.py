#!/usr/bin/env python3
"""Conan recipe for the v7 3.0 embedded JavaScript engine."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class V7Conan(ConanFile):
    name = "v7"
    version = "3.0"
    description = "Embedded JavaScript engine written in C"
    license = "GPL-2.0-only OR Commercial"
    homepage = "https://github.com/cesanta/v7"
    url = "https://github.com/cesanta/v7"
    topics = ("javascript", "embedded", "engine", "c")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_tools(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = executables.get("c")
        if not cc:
            raise ConanException(
                "tools.build:compiler_executables must define c for v7"
            )

        toolchain_dir = os.path.dirname(cc)
        ar = executables.get("ar", os.path.join(toolchain_dir, "llvm-ar"))
        ranlib = executables.get(
            "ranlib", os.path.join(toolchain_dir, "llvm-ranlib")
        )
        for tool in (cc, ar, ranlib):
            if not os.path.isfile(tool):
                raise ConanException(f"Conan toolchain executable not found: {tool}")
        return cc, ar, ranlib

    def build(self):
        apply_conandata_patches(self)
        cc, ar, ranlib = self._compiler_tools()

        # The upstream stack-trace assertion expects the address-free form.
        # Keep this as a make variable so no upstream test source is changed.
        test_flags = "-DV7_FILENAMES_SUPPRESS_CFUNC_ADDR"
        self.run(
            f'make -j1 CC="{cc}" CFLAGS_EXTRA="{test_flags}" v7',
            cwd=self.source_folder,
        )
        self.run(
            f'make -j1 CC="{cc}" CFLAGS_EXTRA="{test_flags}" test',
            cwd=self.source_folder,
        )

        source = os.path.join(self.source_folder, "v7.c")
        object_file = os.path.join(self.build_folder, "v7.o")
        library = os.path.join(self.build_folder, "libv7.a")
        cflags = (
            "-W -Wall -pedantic -Wno-comment -Wno-variadic-macros "
            "-Wno-unused-function -O3 -fPIC -DCS_ENABLE_UTF8"
        )
        self.run(f'"{cc}" {cflags} -c "{source}" -o "{object_file}"')
        self.run(f'"{ar}" rcs "{library}" "{object_file}"')
        self.run(f'"{ranlib}" "{library}"')

    def package(self):
        copy(
            self,
            "v7.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
            keep_path=False,
        )
        copy(
            self,
            "v7",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "libv7.a",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["v7"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "v7")
        self.cpp_info.set_property("cmake_target_name", "v7::v7")
        self.cpp_info.set_property("pkg_config_name", "v7")
