#!/usr/bin/env python3
"""Conan recipe for the aylet command-line player."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AyletConan(ConanFile):
    name = "aylet"
    version = "0.5"
    description = "aylet 0.5"
    license = "GPL-2.0-or-later"
    homepage = "https://www.worldofspectrum.org/"
    url = "https://www.worldofspectrum.org/"

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
        # The upstream Makefile defaults to gcc and does not consume Conan's
        # compiler toolchain configuration.  Pass the profile-selected C
        # compiler explicitly so an OHOS build cannot silently become a host
        # Linux build.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        if not compilers.get("c"):
            raise ConanInvalidConfiguration(
                "aylet builds require tools.build:compiler_executables:c"
            )
        cc = compilers["c"]
        if str(self.settings.os) == "OHOS":
            # The upstream link rule ignores LDFLAGS, so carry -static in CC
            # to avoid producing an ELF that needs the device-only musl loader.
            cc = f"{cc} -static"
        self.run(
            f"make CC=\"{cc}\" -j1 aylet "
            "OBJS='main.o sound.o ui-stdout.o z80.o drv-stdout.o' "
            "CFLAGS='-include stdlib.h -O2 -Wall' "
            "CURSES_LIB=''",
            cwd=self.source_folder,
            env=["conanbuild"],
        )

    def package(self):
        copy(self, "aylet", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "aylet.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
