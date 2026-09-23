#!/usr/bin/env python3
"""Conan recipe for bmkdep 20140112."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class BmkdepConan(ConanFile):
    name = "bmkdep"
    version = "20140112"
    description = "Portable BSD mkdep utility for generating Makefile dependencies"
    license = "BSD-3-Clause"
    homepage = "https://github.com/trociny/bmkdep"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.build = "."
        self.folders.generators = "."

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OS {self.settings.os} is not supported; bmkdep requires Linux or OHOS"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    @staticmethod
    def _quote(value):
        text = str(value).replace("\\", "/")
        return f'"{text}"' if any(ch.isspace() for ch in text) else text

    @staticmethod
    def _string_define(name, value):
        return f'-D{name}=\\"{value}\\"'

    def build(self):
        apply_conandata_patches(self)

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = self._quote(compilers.get("c", "clang"))
        cflags = list(
            self.conf.get("tools.build:cflags", default=[], check_type=list) or []
        )
        exelinkflags = list(
            self.conf.get("tools.build:exelinkflags", default=[], check_type=list) or []
        )

        flags = ["-O2", "-Wall", "-Wextra", "-fPIE"]
        flags.extend(self._quote(flag) for flag in cflags)
        if self.settings.os == "OHOS":
            flags.extend(
                [
                    self._string_define("DEFAULT_CC", "clang"),
                    self._string_define("BMKDEP_PATH_TMP", "/data/local/tmp"),
                    self._string_define(
                        "BMKDEP_PATH_DEFPATH",
                        "/data/service/hnp/bin:/storage/Users/currentUser/usr/local/bin:"
                        "/system/bin:/bin:/usr/bin",
                    ),
                ]
            )

        link_flags = ["-pie", "-Wl,-z,relro,-z,now"]
        link_flags.extend(self._quote(flag) for flag in exelinkflags)
        command = " ".join(
            [cc, *flags, "mkdep.c", "findcc.c", *link_flags, "-o", "bmkdep"]
        )
        self.run(command, cwd=self.source_folder, env="conanbuild")

        # Upstream 20140112 contains no test sources and defines no test/check target.
        self.output.info("Upstream test suite: 0 tests (no test target shipped)")

    def package(self):
        copy(
            self,
            "bmkdep",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "bmkdep.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
