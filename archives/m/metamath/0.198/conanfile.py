#!/usr/bin/env python3
"""Conan recipe for the Metamath proof verifier 0.198."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class MetamathConan(ConanFile):
    name = "metamath"
    version = "0.198"
    description = "A proof verifier and proof assistant for the Metamath language"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/metamath/metamath-exe"
    url = "https://github.com/metamath/metamath-exe"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    _source_url = (
        "https://github.com/metamath/metamath-exe/archive/refs/tags/v0.198.tar.gz"
    )
    _source_sha256 = (
        "7029880b754ee7e7e97b4c1b5e79910222c4f258d353e9b739dc413a4f35551f"
    )
    _source_files = (
        "metamath.c",
        "mmcmdl.c",
        "mmcmds.c",
        "mmdata.c",
        "mmhlpa.c",
        "mmhlpb.c",
        "mminou.c",
        "mmmaci.c",
        "mmpars.c",
        "mmpfas.c",
        "mmunif.c",
        "mmutil.c",
        "mmveri.c",
        "mmvstr.c",
        "mmword.c",
        "mmwtex.c",
    )

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "metamath is adapted for Linux and OHOS only"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            url=self._source_url,
            sha256=self._source_sha256,
            strip_root=True,
        )

    def _compiler(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        return (
            compiler_executables.get("c")
            or os.environ.get("CC")
            or shutil.which("clang")
            or shutil.which("cc")
            or "cc"
        )

    def _ohos_compiler_flags(self, compiler):
        if str(self.settings.os) != "OHOS":
            return []

        arch = str(self.settings.arch)
        target = {
            "armv8": "aarch64-linux-ohos",
            "armv8.3": "aarch64-linux-ohos",
            "armv8_32": "arm-linux-ohos",
            "armv7": "arm-linux-ohos",
            "x86_64": "x86_64-linux-ohos",
        }.get(arch)
        flags = ["--target=" + target] if target else []
        flags.append("-D__MUSL__")

        configured_sysroot = self.conf.get(
            "tools.build:sysroot",
            default="",
            check_type=str,
        )
        sysroot = configured_sysroot
        if not sysroot and os.path.isfile(compiler):
            candidate = os.path.normpath(
                os.path.join(os.path.dirname(compiler), "..", "..", "sysroot")
            )
            if os.path.isdir(os.path.join(candidate, "usr", "include")):
                sysroot = candidate
        if sysroot:
            flags.append('--sysroot="' + sysroot + '"')
        return flags

    @staticmethod
    def _quote(value):
        if " " in value or "\t" in value:
            return f'"{value.replace(chr(34), chr(92) + chr(34))}"'
        return value

    def build(self):
        compiler = self._quote(self._compiler())
        output = os.path.join(self.build_folder, "metamath")
        command = [
            compiler,
            *self._ohos_compiler_flags(self._compiler()),
            "-O3",
            "-funroll-loops",
            "-finline-functions",
            "-fomit-frame-pointer",
            "-DINLINE=inline",
            "-Wall",
            "-Wextra",
            *self._source_files,
            "-o",
            self._quote(output),
        ]
        self.run(" ".join(command), cwd=self.source_folder)

    def package(self):
        copy(
            self,
            "metamath",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "metamath.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE.TXT",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
