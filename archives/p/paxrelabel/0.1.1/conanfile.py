#!/usr/bin/env python3
"""Conan recipe for paxrelabel 0.1.1."""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PaxrelabelConan(ConanFile):
    name = "paxrelabel"
    version = "0.1.1"
    description = "Package-level PaX flag management tool"
    license = "ISC"
    homepage = "https://gitlab.alpinelinux.org/ariadne/paxrelabel"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c")
        if not cc:
            cc = "gcc" if str(self.settings.compiler) == "gcc" else "clang"
        build_type_flags = {
            "Debug": "-O0 -g",
            "Release": "-O2 -DNDEBUG",
            "RelWithDebInfo": "-O2 -g -DNDEBUG",
            "MinSizeRel": "-Os -DNDEBUG",
        }
        cflags = (
            f"{build_type_flags.get(str(self.settings.build_type), '-O2 -DNDEBUG')} "
            "-fPIC -Wall -std=gnu2x -pedantic"
        )

        self.run(
            f'make -C "{self.source_folder}" CC="{cc}" CFLAGS="{cflags}" -j1',
            env="conanbuild",
        )

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "paxrelabel"))
        copy(self, "paxrelabel", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
