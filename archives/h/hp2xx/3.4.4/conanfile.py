#!/usr/bin/env python3
"""Conan recipe for hp2xx 3.4.4.

hp2xx converts HP-GL plotter files into vector and raster formats.  The
upstream build is a hand-edited Makefile under sources/, so this recipe builds
a minimal CLI profile with the no-preview backend and no optional image
libraries.
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class Hp2xxConan(ConanFile):
    name = "hp2xx"
    version = "3.4.4"
    description = "HP-GL converter into vector and raster formats"
    license = "GPL-2.0-or-later"
    homepage = "https://www.gnu.org/software/hp2xx/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # sources/Makefile builds in place and emits sources/hp2xx.
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"hp2xx only supports Linux/OHOS in this recipe, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _source_subdir(self):
        return os.path.join(self.source_folder, "sources")

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get("c", "clang")

    def _cflags(self):
        if self.settings.build_type == "Debug":
            opt = "-g -O0"
        else:
            opt = "-O2"
        # -DUNIX selects the portable Unix code path; do not enable HAS_UNIX_X11.
        # HP2XX_USE_MKSTEMP avoids OHOS tmpfile() defaulting to an unwritable path.
        return (
            f"{opt} -DUNIX -DHP2XX_USE_MKSTEMP -Wall -Wuninitialized -Wunused "
            "-Wreturn-type -Wmissing-prototypes -Wstrict-prototypes"
        )

    def build(self):
        apply_conandata_patches(self)
        src = self._source_subdir()
        cc = self._compiler()
        cflags = self._cflags()

        self.run(
            'make hp2xx -j1 '
            f'CC="{cc}" CFLAGS="{cflags}" CPPFLAGS="-I." LFLAGS="" '
            'DEFINES="-DUNIX" PREVIEWER=no_prev ALL_LIBS="-lm" '
            'EX_SRC="" EX_OBJ="" EX_DEFS="" EX_LIBS=""',
            cwd=src,
            env=["conanbuild"],
        )

        smoke = os.path.join(src, "conan-smoke.svg")
        sample = os.path.join(self.source_folder, "hp-tests", "colors.hp")
        self.run(
            f'./hp2xx -q -m svg -f "{smoke}" "{sample}"',
            cwd=src,
            env=["conanbuild"],
        )
        with open(smoke, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read()
        if "<svg" not in data or "<path" not in data:
            raise ConanException("hp2xx SVG smoke conversion did not produce expected output")

    def package(self):
        src = self._source_subdir()
        copy(self, "hp2xx", src=src, dst=os.path.join(self.package_folder, "bin"))
        copy(
            self,
            "hp2xx.1",
            src=os.path.join(self.source_folder, "doc"),
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
        )
        copy(self, "copying", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        for doc in ("README", "AUTHORS", "CHANGES", "TODO"):
            copy(
                self,
                doc,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "share", "doc", "hp2xx"),
            )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
