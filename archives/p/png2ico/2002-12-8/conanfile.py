#!/usr/bin/env python3
"""Conan recipe for the png2ico 2002-12-08 command-line application."""

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


class Png2icoConan(ConanFile):
    name = "png2ico"
    version = "2002-12-8"
    description = "PNG to Windows ICO command-line converter"
    license = "GPL-2.0-only"
    homepage = "https://www.winterdrache.de/freeware/png2ico/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpng/1.6.58.2")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "png2ico supports only Linux and OHOS builds"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        data = self.conan_data["sources"]
        get(self, **data, strip_root=True)

    @staticmethod
    def _quote(value):
        if os.name == "nt":
            return '"' + str(value).replace('"', '\\"') + '"'
        return shlex.quote(str(value))

    def _compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return str(executables.get("cpp") or "c++")

    def _dependency_flags(self):
        include_dirs = []
        library_dirs = []
        libraries = []
        system_libraries = []
        for name in ("libpng", "zlib"):
            if name not in self.dependencies:
                continue
            cpp_info = self.dependencies[name].cpp_info
            include_dirs.extend(cpp_info.includedirs)
            library_dirs.extend(cpp_info.libdirs)
            libraries.extend(cpp_info.libs)
            system_libraries.extend(cpp_info.system_libs)

        include_flags = ["-I" + str(path) for path in include_dirs]
        link_flags = ["-L" + str(path) for path in library_dirs]
        link_flags.extend("-l" + str(library) for library in libraries)
        link_flags.extend("-l" + str(library) for library in system_libraries)
        return include_flags, link_flags

    def _target_flags(self):
        flags = [
            str(flag)
            for flag in self.conf.get("tools.build:cxxflags", default=[],
                                     check_type=list)
        ]
        if str(self.settings.os) == "OHOS":
            if not any(flag.startswith("--target=") for flag in flags):
                flags.append("--target=aarch64-linux-ohos")
            sysroot = self.conf.get("tools.build:sysroot", default=None)
            if sysroot and not any(flag.startswith("--sysroot=") for flag in flags):
                flags.append("--sysroot=" + str(sysroot))
        return flags

    def build(self):
        apply_conandata_patches(self)

        source = os.path.join(self.source_folder, "png2ico.cpp")
        output = os.path.join(self.build_folder, "png2ico")
        include_flags, link_flags = self._dependency_flags()
        command = [
            self._compiler(),
            "-std=gnu++17",
            "-O2",
            "-Wall",
            "-Wextra",
            "-finline-functions",
        ]
        command.extend(self._target_flags())
        command.extend(include_flags)
        command.extend([source, "-o", output])
        command.extend(link_flags)
        command.extend(
            str(flag)
            for flag in self.conf.get("tools.build:exelinkflags", default=[],
                                     check_type=list)
        )
        self.run(" ".join(self._quote(item) for item in command),
                 cwd=self.source_folder)

    def package(self):
        copy(self, "png2ico", self.build_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "png2ico.1", os.path.join(self.source_folder, "doc"),
             os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "README*", self.source_folder,
             os.path.join(self.package_folder, "share", "doc", "png2ico"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
