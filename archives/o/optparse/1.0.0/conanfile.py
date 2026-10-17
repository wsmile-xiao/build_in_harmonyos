#!/usr/bin/env python3
"""Conan recipe for optparse — header-only library."""
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


class OptparseConan(ConanFile):
    name = "optparse"
    version = "1.0.0"
    description = "Portable, reentrant, embeddable, getopt-like option parser"
    license = "Unlicense"
    homepage = "https://github.com/skeeto/optparse"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = compiler_executables.get("c")
        if not compiler:
            raise ConanException(
                "tools.build:compiler_executables must define the C compiler"
            )
        self.run(
            f'make -C "{self.source_folder}" test CC="{compiler}"'
        )
        self.run(
            os.path.join(self.source_folder, "test"),
            cwd=self.source_folder,
        )

    def package(self):
        copy(
            self,
            "optparse.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
            keep_path=False,
        )
        copy(
            self,
            "UNLICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
