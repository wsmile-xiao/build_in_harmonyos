#!/usr/bin/env python3
"""Conan recipe for JH71xx-tools 0-2021.07.16-git43be3329."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class Jh71xxToolsConan(ConanFile):
    name = "jh71xx-tools"
    version = "0-2021.07.16-git43be3329"
    description = "StarFive JH7100 bootloader recovery and updater over UART/XMODEM"
    license = "MIT"
    homepage = "https://github.com/xypron/JH71xx-tools"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} is not supported; use Linux or OHOS"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("c")
        if compiler:
            return compiler
        if cross_building(self):
            raise ConanInvalidConfiguration(
                "cross builds require tools.build:compiler_executables[c]"
            )
        return "cc"

    def _conf_flags(self, name):
        values = self.conf.get(name, default=[], check_type=list) or []
        return " ".join(str(value) for value in values)

    def build(self):
        apply_conandata_patches(self)
        compiler = self._compiler()
        build_flags = {
            "Debug": "-O0 -g",
            "Release": "-O2 -DNDEBUG",
            "RelWithDebInfo": "-O2 -g -DNDEBUG",
            "MinSizeRel": "-Os -DNDEBUG",
        }[str(self.settings.build_type)]
        cflags = self._conf_flags("tools.build:cflags")
        linkflags = self._conf_flags("tools.build:exelinkflags")
        source = os.path.join(self.source_folder, "jh7100-recover.c").replace(
            "\\", "/"
        )
        output = os.path.join(self.build_folder, "jh7100-recover").replace(
            "\\", "/"
        )
        self.run(
            f'"{compiler}" -Wall -fPIE {build_flags} {cflags} '
            f'"{source}" {linkflags} -o "{output}"',
            env=["conanbuild"],
        )

    def package(self):
        copy(
            self,
            "jh7100-recover",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "README.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "doc", "jh71xx-tools"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
