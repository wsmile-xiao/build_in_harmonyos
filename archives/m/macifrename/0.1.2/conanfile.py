#!/usr/bin/env python3
"""Conan recipe for macifrename 0.1.2."""

import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import copy, get, replace_in_file
from conan.tools.layout import basic_layout


class MacifrenameConan(ConanFile):
    name = "macifrename"
    version = "0.1.2"
    description = "Stably rename NIC names based on MAC addresses"
    license = "ISC"
    homepage = "https://git.sr.ht/~kaniini/macifrename"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        sources = self.conan_data["sources"]
        try:
            get(self, url=sources["url"], sha256=sources["sha256"], strip_root=True)
        except ConanException as error:
            self.output.warning(
                "official sourcehut archive download failed locally; "
                f"falling back to Alpine distfile mirror with the same hash: {error}"
            )
            get(self, url=sources["mirror_url"], sha256=sources["sha256"], strip_root=True)
        replace_in_file(
            self,
            os.path.join(self.source_folder, "macifrename.c"),
            "#include <linux/if.h>",
            "#include <net/if.h>",
        )

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c")
        if not cc:
            if cross_building(self):
                raise ConanInvalidConfiguration("cross builds require tools.build:compiler_executables[c]")
            cc = "cc"

        build_type_flags = {
            "Debug": "-O0 -g",
            "Release": "-O2 -DNDEBUG",
            "RelWithDebInfo": "-O2 -g -DNDEBUG",
            "MinSizeRel": "-Os -DNDEBUG",
        }
        cflags = (
            "-D_GNU_SOURCE -Werror -Wall -Wextra -pedantic -std=gnu99 -fPIC "
            f"{build_type_flags[str(self.settings.build_type)]}"
        )
        self.run(
            f'make CC="{cc}" CFLAGS="{cflags}" LDFLAGS="" -j1',
            cwd=self.source_folder,
            env=["conanbuild"],
        )

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "macifrename", self.source_folder, os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
