#!/usr/bin/env python3
"""Conan recipe for afio 2.5.2."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class AfioConan(ConanFile):
    name = "afio"
    version = "2.5.2"
    description = "Archive file manipulation and backup utility"
    license = "LicenseRef-Afio AND LGPL-2.0-or-later"
    homepage = "https://github.com/kholtman/afio"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

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
        compiler = self._compiler()
        build_flags = {
            "Debug": "-O0 -g",
            "Release": "-O2 -DNDEBUG",
            "RelWithDebInfo": "-O2 -g -DNDEBUG",
            "MinSizeRel": "-Os -DNDEBUG",
        }
        definitions = (
            "-D_FILE_OFFSET_BITS=64 -D_LARGEFILE_SOURCE -DMEMCPY -DMKDIR "
            "-DVOIDFIX -DHAVEFCNTL -DHAVEMEMCMP -DHAVE_LCHOWN "
            '-DDEFFMTCMD=\\"fdformat\\x20/dev/fd0H1440\\" '
            '-DPRG_COMPRESS=\\"gzip\\" -DHAVEFNMATCH'
        )
        flags = (
            f"-std=gnu99 -Wall -Wformat -Werror=format-security -Wno-unused-result "
            f"-fPIE {build_flags[str(self.settings.build_type)]} "
            f"{self._conf_flags('tools.build:cflags')} {definitions}"
        )
        objects = []
        for source_name in ("afio.c", "compfile.c", "exten.c", "match.c"):
            source = os.path.join(self.source_folder, source_name)
            obj = os.path.join(self.build_folder, source_name + ".o")
            self.run(
                f'"{compiler}" {flags} -I"{self.source_folder}" -c "{source}" -o "{obj}"',
                env=["conanbuild"],
            )
            objects.append(obj)
        output = os.path.join(self.build_folder, "afio")
        quoted_objects = " ".join(f'"{path}"' for path in objects)
        self.run(
            f'"{compiler}" {flags} {quoted_objects} '
            f'{self._conf_flags("tools.build:exelinkflags")} -o "{output}"',
            env=["conanbuild"],
        )

    def package(self):
        copy(self, "afio.c", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "afio_license_issues_v5.txt", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "afio", self.build_folder, os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "afio.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)
        if os.name != "nt":
            os.chmod(os.path.join(self.package_folder, "bin", "afio"), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
