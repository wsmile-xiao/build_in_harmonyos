#!/usr/bin/env python3
"""Conan recipe for cmospwd 5.0 (CMOS/BIOS password recovery tool, C/makefile) on HarmonyOS PC."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class CmospwdConan(ConanFile):
    name = "cmospwd"
    version = "5.0"
    description = "CmosPwd decrypts passwords stored in CMOS used to access BIOS SETUP"
    license = "GPL-2.0-or-later"
    homepage = "https://www.cgsecurity.org/wiki/CmosPwd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cmospwd {self.version} only supports Linux and OHOS, got os={self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = compilers.get("c", "clang")
        src = os.path.join(self.source_folder, "src", "cmospwd.c")
        out = os.path.join(self.build_folder, "cmospwd")
        self.run(f'{cc} -Wall -W -O2 -D__linux__=1 -o "{out}" "{src}"')
        self.output.info("upstream test audit: cmospwd-5.0 has no test suite")
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            '{"status":"no_tests","framework":"none",'
            '"command":"",'
            '"discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,'
            '"reason":"upstream cmospwd-5.0 has no test suite: single Makefile target '
            'cmospwd only, no check/test target, no tests directory"}'
        )

    def package(self):
        copy(self, "cmospwd", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "cmospwd.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
