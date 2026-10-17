#!/usr/bin/env python3
"""Conan recipe for libtomfloat 0.02 — plain GNU makefile static library.

The upstream makefile has no configure step; its default target builds
libtomfloat.a only. make(1) defaults to CC=cc / AR=ar, which do not exist
on the OHOS toolchain, so the executables are passed explicitly from
tools.build:compiler_executables (R33). The public header tomfloat.h
includes <tommath.h>, so dependency include paths are passed to make via
CPPFLAGS (GNU make implicit rule: $(CC) $(CPPFLAGS) $(CFLAGS) -c).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibtomfloatConan(ConanFile):
    name = "libtomfloat"
    version = "0.02"
    description = "C library for multiple-precision floating-point arithmetic built on LibTomMath"
    license = "Public Domain"
    homepage = "https://github.com/libtom/libtomfloat"
    url = "https://github.com/libtom/libtomfloat"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libtommath/1.3.0")

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
            raise ConanInvalidConfiguration(
                "libtomfloat 0.02 upstream builds a static library only"
            )

    def build(self):
        apply_conandata_patches(self)
        cc, ar, ranlib = self._compiler_tools()
        make_args = f"CC={cc} AR={ar} RANLIB={ranlib} -j1"
        cppflags = " ".join(
            f"-I{inc}"
            for dep in self.dependencies.host.values()
            for inc in dep.cpp_info.includedirs
        )
        if cppflags:
            make_args += f" CPPFLAGS={cppflags}"
        self.run(f"make {make_args}", cwd=self.source_folder)

    def package(self):
        copy(
            self,
            "tomfloat.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "libtomfloat.a",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )

    def package_info(self):
        self.cpp_info.libs = ["tomfloat"]
        # tomfloat.h includes <tommath.h>: consumers get the libtommath
        # include path propagated through the dependency graph.
        self.cpp_info.requires = ["libtommath::libtommath"]
