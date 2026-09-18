#!/usr/bin/env python3
"""Conan recipe for libopenv2g 0.9.5.

The upstream archive contains Eclipse-generated makefiles for an executable
example. The recipe exports a small, reproducible Makefile
that builds the reusable EXI/V2GTP implementation as libopenv2g.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class Libopenv2gConan(ConanFile):
    name = "libopenv2g"
    version = "0.9.5"
    description = "C library implementing ISO 15118 and DIN 70121 EXI codecs plus V2GTP framing"
    license = "LGPL-3.0-only"
    homepage = "https://sourceforge.net/projects/openv2g/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "Makefile", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        pass

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libopenv2g supports Linux and OHOS, not %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self)
        # The exported Makefile is an in-source Makefile, like the upstream
        # Eclipse project. Keeping its build directory in the source tree also
        # lets the generated dependency files follow the normal make rules.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=False)

    @staticmethod
    def _quote(value):
        return shlex.quote(str(value))

    def _compiler_tools(self):
        tools = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        if not isinstance(tools, dict):
            tools = {}
        return (
            tools.get("c", "clang"),
            tools.get("ar", "llvm-ar"),
            tools.get("ranlib", "llvm-ranlib"),
        )

    def build(self):
        apply_conandata_patches(self)
        cc, ar, ranlib = self._compiler_tools()
        shared = "1" if bool(self.options.shared) else "0"
        command = (
            "make"
            " CC=%s AR=%s RANLIB=%s SHARED=%s -j1"
            % (self._quote(cc), self._quote(ar), self._quote(ranlib), shared)
        )
        self.run(command, cwd=self.source_folder)
        # OpenV2G 0.9.5 has no upstream test/check target. Its src/test
        # directory contains interactive/example programs, not a registered
        # test suite; consumer API coverage is run by test_package.

    def package(self):
        shared = "1" if bool(self.options.shared) else "0"
        # The exported install target places lib/ and include/ directly below
        # the Conan package folder when PREFIX=/ is used.
        command = (
            "make install PREFIX=/ DESTDIR=%s SHARED=%s"
            % (self._quote(self.package_folder), shared)
        )
        self.run(command, cwd=self.source_folder)
        copy(
            self,
            "LICENSE.txt",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["openv2g"]
