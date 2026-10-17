#!/usr/bin/env python3
"""Conan recipe — datefudge 1.27 (Makefile)."""

import os
import platform
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class DatefudgeConan(ConanFile):
    name = "datefudge"
    version = "1.27"
    description = "Fake the system date for a process without changing the system clock"
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/debian/datefudge"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Both the launcher and the official test target use GNU date's
        # --date parser, which is not provided by the OHOS system date tool.
        self.requires("coreutils/9.10", headers=False, libs=False, run=True)

    def build_requirements(self):
        # The OHOS worker's system Perl does not honor LD_PRELOAD for time(),
        # while the published Conan Perl is a compatible dynamic executable.
        if str(self.settings.os) == "OHOS":
            self.test_requires("perl/5.42.2")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "datefudge requires a POSIX dynamic loader with LD_PRELOAD support"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or "cc"
        test_environment = Environment()
        if self._can_run_ohos_binaries():
            coreutils_bin = os.path.join(
                self.dependencies["coreutils"].package_folder, "bin"
            )
            test_environment.prepend_path("PATH", coreutils_bin)
        with test_environment.vars(self).apply():
            self.run(
                f'make -j1 CC="{cc}" VERSION="{self.version}" prefix=/usr',
                cwd=self.source_folder,
            )
            self._run_upstream_tests()

    def package(self):
        copy(
            self,
            "datefudge",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "datefudge.so",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "lib", "datefudge"),
            keep_path=False,
        )
        copy(
            self,
            "datefudge.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        os.chmod(os.path.join(self.package_folder, "bin", "datefudge"), 0o755)
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_library()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]

    def _run_upstream_tests(self):
        target_is_ohos = str(self.settings.os) == "OHOS"
        if target_is_ohos and self._can_run_ohos_binaries():
            perl = os.path.join(
                self.dependencies.test["perl"].package_folder, "bin", "perl"
            )
            if not os.path.isfile(perl):
                raise ConanException(f"HarmonyOS test interpreter is missing: {perl}")
            self.run(f'make test PERL="{perl}"', cwd=self.source_folder)
            return

        if not target_is_ohos:
            self.run("make test", cwd=self.source_folder)
            return

        test_dir = os.path.join(self.build_folder, "upstream-native-tests")
        os.makedirs(test_dir, exist_ok=True)
        for filename in (
            "Makefile",
            "datefudge.c",
            "datefudge64.c",
            "datefudge.sh",
            "datefudge.man",
        ):
            shutil.copy2(
                os.path.join(self.source_folder, filename),
                os.path.join(test_dir, filename),
            )
        os.makedirs(os.path.join(test_dir, "debian"), exist_ok=True)
        shutil.copy2(
            os.path.join(self.source_folder, "debian", "changelog"),
            os.path.join(test_dir, "debian", "changelog"),
        )
        self.run(
            f'make -j1 CC="cc" VERSION="{self.version}" prefix=/usr',
            cwd=test_dir,
        )
        self.run("make test", cwd=test_dir)

    def _can_run_ohos_binaries(self):
        return str(self.settings.os) == "OHOS" and platform.machine().lower() in (
            "aarch64",
            "arm64",
        )

    def _sign_ohos_library(self):
        library = os.path.join(
            self.package_folder, "lib", "datefudge", "datefudge.so"
        )
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = (
            shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            raise ConanException("HarmonyOS ELF signing tools are unavailable")
        self.run(f'"{objcopy}" --remove-section .codesign "{library}"')
        self.run(
            f'"{signer}" sign -inFile "{library}" -outFile "{library}" -selfSign 1'
        )
