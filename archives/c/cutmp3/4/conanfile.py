#!/usr/bin/env python3
"""Conan recipe — cutmp3 4 (Makefile C command-line application)."""

import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class Cutmp3Conan(ConanFile):
    name = "cutmp3"
    description = "Lossless command-line MP3 and MP2 frame cutter"
    license = "GPL-2.0-or-later"
    homepage = "https://www.puchalla-online.de/cutmp3.html"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def set_version(self):
        # Conan 2 requires a version slug of at least two characters. The
        # task directory remains `4`; the artifact uses upstream version 4.0.
        self.version = "4.0"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("readline/8.3")
        self.requires("ncurses/6.6")
        self.requires("mpg123/1.33.5", run=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} is not supported"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c")
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

    def _include_flags(self):
        flags = []
        for dependency_name in ("readline", "ncurses"):
            dependency = self.dependencies[dependency_name]
            for directory in dependency.cpp_info.includedirs:
                flags.append(f'-I"{directory}"')
        return " ".join(flags)

    def _static_library(self, dependency_name, filenames):
        dependency = self.dependencies[dependency_name]
        for directory in dependency.cpp_info.libdirs:
            for filename in filenames:
                candidate = os.path.join(directory, filename)
                if os.path.isfile(candidate):
                    return candidate
        raise ConanException(
            f"{dependency_name} does not provide any of: {', '.join(filenames)}"
        )

    def build(self):
        apply_conandata_patches(self)

        compiler = self._compiler()
        include_flags = self._include_flags()
        configured_cflags = self._conf_flags("tools.build:cflags")
        configured_linkflags = self._conf_flags("tools.build:exelinkflags")
        build_type_flags = {
            "Debug": "-O0 -g",
            "Release": "-O2 -DNDEBUG",
            "RelWithDebInfo": "-O2 -g -DNDEBUG",
            "MinSizeRel": "-Os -DNDEBUG",
        }[str(self.settings.build_type)]
        common_flags = (
            f"-std=gnu11 -Wall -Wformat-security -Wunused-result "
            f"-fPIC -fPIE -fstack-protector-strong -D_FORTIFY_SOURCE=2 "
            f"{build_type_flags} {configured_cflags} {include_flags}"
        )

        main_source = os.path.join(self.source_folder, "main.c")
        mpglib_source = os.path.join(self.source_folder, "mpglib.c")
        main_object = os.path.join(self.build_folder, "main.o")
        mpglib_object = os.path.join(self.build_folder, "mpglib.o")
        executable = os.path.join(self.build_folder, "cutmp3")
        readline = self._static_library("readline", ("libreadline.a",))
        ncurses = self._static_library(
            "ncurses", ("libncursesw.a", "libncurses.a")
        )

        self.run(
            f'"{compiler}" {common_flags} -DVERSION=\\"4.0\\" '
            f'-c "{main_source}" -o "{main_object}"',
            env="conanbuild",
        )
        self.run(
            f'"{compiler}" {common_flags} '
            f'-c "{mpglib_source}" -o "{mpglib_object}"',
            env="conanbuild",
        )
        self.run(
            f'"{compiler}" -static-pie -Wl,-z,relro,-z,now '
            f'{configured_linkflags} -o "{executable}" "{main_object}" '
            f'"{mpglib_object}" "{readline}" "{ncurses}" -lm',
            env="conanbuild",
        )

    def package(self):
        copy(
            self,
            "cutmp3",
            self.build_folder,
            os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "COPYING",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "README*",
            self.source_folder,
            os.path.join(self.package_folder, "share", "doc", "cutmp3"),
            keep_path=False,
        )
        copy(
            self,
            "USAGE",
            self.source_folder,
            os.path.join(self.package_folder, "share", "doc", "cutmp3"),
            keep_path=False,
        )
        copy(
            self,
            "cutmp3.1",
            self.source_folder,
            os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )
        if os.name != "nt":
            os.chmod(os.path.join(self.package_folder, "bin", "cutmp3"), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
