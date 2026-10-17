#!/usr/bin/env python3
"""Conan recipe — vblade 25 (minimal AoE storage target, Makefile)."""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, save
from conan.tools.layout import basic_layout


class VbladeConan(ConanFile):
    name = "vblade"
    version = "25"
    description = "Minimal userland ATA over Ethernet (AoE) storage target"
    license = "GPL-2.0-only"
    homepage = "https://github.com/OpenAoE/vblade"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"vblade is a Linux/HarmonyOS raw-socket tool, not supported on {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        data = self.conan_data["sources"]
        if isinstance(data, list):
            data = data[0]
        from conan.tools.files import get
        get(self, **data, strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _compiler(self):
        executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        configured = executables.get("c")
        if configured:
            path = str(configured).split()[0].strip("\"'")
            if os.path.isfile(path):
                return configured
        for candidate in ("clang", "cc", "gcc"):
            found = shutil.which(candidate)
            if found:
                return found
        return configured or "clang"

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler()
        # Upstream makefile hardcodes CC = gcc and appends its own CFLAGS.
        # Override CC on the make command line so the OHOS clang is used
        # for both the config.h probe (config/u64.c) and all objects.
        # R33: compiler comes from Conan conf, never from shell env.
        self.run(f"make CC={cc} -j1", cwd=self.source_folder)
        try:
            upstream = {
                "status": "no_tests",
                "framework": "makefile",
                "command": "make check",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "vblade-25 audited: tarball vblade-vblade-25 (sha256 ce498da9...) contains no tests/ or test/ dir and no *test* files; makefile defines only vblade/clean/install targets, no check/test target; make -n check is a make no-op",
            }
            msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
            print(msg, flush=True)
            self.output.info(msg)
        except Exception:
            pass

    def package(self):
        copy(self, "vblade", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "vbladed", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "vblade.8", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man8"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        # Keep a build log snippet for audit trail (best effort, never fails the package).
        try:
            save(self, os.path.join(self.package_folder, "licenses", "BUILD.txt"),
                 f"vblade {self.version} built with make CC override on {self.settings.os}/{self.settings.arch}\n")
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
