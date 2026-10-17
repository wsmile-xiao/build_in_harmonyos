#!/usr/bin/env python3
"""Conan recipe for the cpipe 3.0.1 HarmonyOS AArch64 application."""

import json
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class CpipeConan(ConanFile):
    name = "cpipe"
    version = "3.0.1"
    description = "Copy stdin to stdout while measuring pipe throughput"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/cpipe.berlios/"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        target_os = str(self.settings.os)
        target_version = self.settings.get_safe("os.version")
        target_arch = str(self.settings.arch)
        if (
            target_os != "OHOS"
            or str(target_version) != "6.0"
            or target_arch != "armv8"
        ):
            raise ConanInvalidConfiguration(
                "cpipe/3.0.1 release artifacts require "
                "os=OHOS, os.version=6.0, and arch=armv8"
            )

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    @staticmethod
    def _preserve_generated_files(source_folder):
        specification = os.path.join(source_folder, "cmdline.cli")
        generated = ("cmdline.c", "cmdline.h", "cpipe.1")
        generated_time = os.stat(specification).st_mtime + 1
        for filename in generated:
            path = os.path.join(source_folder, filename)
            os.utime(path, (generated_time, generated_time))

    def build(self):
        compiler_exes = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_exes.get("c")
        if not cc:
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables must provide the C compiler"
            )

        try:
            make = self.conf.get(
                "user.hmbs:make_path", default="make", check_type=str
            ) or "make"
        except Exception:
            make = "make"

        copy(self, "*", src=self.source_folder, dst=self.build_folder)
        self._preserve_generated_files(self.build_folder)
        self.run(
            f'"{make}" CC="{cc}" '
            'CFLAGS="-O2 -Wall -Wextra -Werror=format" -j1 cpipe',
            cwd=self.build_folder,
        )

        marker = {
            "status": "no_tests",
            "framework": "make",
            "command": (
                "make CC=<conan-c-compiler> "
                "CFLAGS='-O2 -Wall -Wextra -Werror=format' -j1 cpipe"
            ),
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "cpipe 3.0.1 upstream tarball has no tests directory, test files, "
                "or check/test target in its raw Makefile"
            ),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))

    def package(self):
        copy(
            self,
            "cpipe",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        os.chmod(os.path.join(self.package_folder, "bin", "cpipe"), 0o755)
        copy(
            self,
            "cpipe.1",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
        )
        copy(
            self,
            "COPYING-2.0",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
