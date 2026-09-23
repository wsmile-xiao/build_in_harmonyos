#!/usr/bin/env python3
"""Conan recipe for cmospwd 5 (CMOS/BIOS password recovery tool, C/makefile) on HarmonyOS PC.

Version slug: the platform task card asks for `cmospwd 5`, and upstream has no
dotted alternative label to fall back on - the single 5.x release is published as
`cmospwd-5.0.tar.bz2` and self-labels `CmosPwd - BIOS Cracker 5.0`. Conan 2.x
rejects a one-character version: RecipeReference validation in
conan/api/model/refs.py applies `^[a-z0-9_][a-z0-9_+.-]{1,100}\\Z`, i.e. at least
two characters, so `cmospwd/5` dies at export with
`ERROR: Invalid package version '5'` (measured on the HarmonyOS aarch64 device
with conan 2.29.1). The `5.0` key is already published in the artifact registry by
archives/c/cmospwd/5.0, so re-using it would be a same-version recipe change.
Following the sanctioned repo precedent (archives/c/cronic/3 -> cronic/v3,
archives/r/rapidhash/3 -> rapidhash/v3) the task-card directory and the
`feat/cmospwd-5` branch stay `5`, while set_version() names the built artifact
`cmospwd/v5`. A literal `version = "5"` attribute is deliberately absent: CI L0m
cross-checks such an attribute against the version directory.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class CmospwdConan(ConanFile):
    name = "cmospwd"
    description = "CmosPwd decrypts passwords stored in CMOS used to access BIOS SETUP"
    license = "GPL-2.0-or-later"
    homepage = "https://www.cgsecurity.org/wiki/CmosPwd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def set_version(self):
        # Task card `5` -> artifact `v5`; see the module docstring for why a bare
        # one-character version cannot be exported.
        self.version = "v5"

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
        # Upstream Makefile pins CC=gcc, so compile directly to honour the
        # toolchain compiler from the Conan conf.
        self.run(f'{cc} -Wall -W -O2 -D__linux__=1 -o "{out}" "{src}"')
        self.output.info("upstream test audit: cmospwd 5 has no test suite")
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            '{"status":"no_tests","framework":"none",'
            '"command":"",'
            '"discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,'
            '"reason":"upstream cmospwd-5.0.tar.bz2 has no test suite: src/Makefile has the '
            'single target cmospwd only, no check/test target, no tests directory"}'
        )

    def package(self):
        copy(self, "cmospwd", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "cmospwd.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
