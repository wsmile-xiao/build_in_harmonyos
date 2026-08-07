#!/usr/bin/env python3
"""Conan recipe for abootimg 0.6."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


class AbootimgConan(ConanFile):
    name = "abootimg"
    version = "0.6"
    description = "Tool to inspect, create, and update Android boot images"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ggrandou/abootimg"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} is not supported")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

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

    def build(self):
        apply_conandata_patches(self)
        save(
            self,
            os.path.join(self.build_folder, "version.h"),
            '#define VERSION_STR "0.6"\n',
        )
        build_flags = {
            "Debug": "-O0 -g",
            "Release": "-O2 -DNDEBUG",
            "RelWithDebInfo": "-O2 -g -DNDEBUG",
            "MinSizeRel": "-Os -DNDEBUG",
        }
        compiler = self._compiler()
        source = os.path.join(self.source_folder, "abootimg.c").replace("\\", "/")
        output = os.path.join(self.build_folder, "abootimg").replace("\\", "/")
        source_include = self.source_folder.replace("\\", "/")
        build_include = self.build_folder.replace("\\", "/")
        flags = build_flags[str(self.settings.build_type)]
        extra_cflags = self._conf_flags("tools.build:cflags")
        extra_linkflags = self._conf_flags("tools.build:exelinkflags")
        self.run(
            f'"{compiler}" -std=gnu99 -Wall -Wextra -fPIE {flags} '
            f'{extra_cflags} -I"{build_include}" -I"{source_include}" '
            f'"{source}" {extra_linkflags} -o "{output}"',
            env=["conanbuild"],
        )

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README", self.source_folder, os.path.join(self.package_folder, "share", "doc", "abootimg"), keep_path=False)
        copy(self, "abootimg-pack-initrd", self.source_folder, os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "abootimg-unpack-initrd", self.source_folder, os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "abootimg", self.build_folder, os.path.join(self.package_folder, "bin"), keep_path=False)
        if os.name != "nt":
            for name in ("abootimg", "abootimg-pack-initrd", "abootimg-unpack-initrd"):
                os.chmod(os.path.join(self.package_folder, "bin", name), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
