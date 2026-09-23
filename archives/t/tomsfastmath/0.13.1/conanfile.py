#!/usr/bin/env python3
"""Conan recipe — tomsfastmath 0.13.1 (fast multiple-precision integer library).

TomsFastMath by the libtom project — a fast, portable bignum library. The
upstream makefile builds the static library libtfm.a and the demo test
programs; this recipe drives the upstream makefile directly (CC/AR/RANLIB
from conan conf, R33-compliant) and also runs the upstream self tests.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout


class TomsFastMathConan(ConanFile):
    name = "tomsfastmath"
    version = "0.13.1"
    description = "TomsFastMath — a fast, portable, easy to use bignum library"
    license = ("Apache-2.0",)
    homepage = "https://github.com/libtom/tomsfastmath"
    url = "https://github.com/libtom/tomsfastmath"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_tools(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return (
            executables.get("c", "clang"),
            executables.get("ar", "llvm-ar"),
            executables.get("ranlib", "llvm-ranlib"),
        )

    def validate(self):
        if self.options.shared:
            raise ConanInvalidConfiguration("tomsfastmath 0.13.1 upstream makefile builds only the static library")

    def build(self):
        apply_conandata_patches(self)
        cc, ar, ranlib = self._compiler_tools()
        make_args = f"CC={cc} AR={ar} RANLIB={ranlib} -j2"
        self.run(f"make {make_args}", cwd=self.source_folder)
        self.run(f"make {make_args} test_standalone", cwd=self.source_folder)
        # Build and run the upstream demo tests (self test + full suite).
        self.run(
            f"{cc} -O2 -Isrc/headers demo/stest.c libtfm.a -o stest",
            cwd=self.source_folder,
        )
        self.run("./stest", cwd=self.source_folder)
        self.run("./test", cwd=self.source_folder)

    def package(self):
        copy(
            self,
            "tfm.h",
            src=os.path.join(self.source_folder, "src", "headers"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "libtfm.a",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["tfm"]
