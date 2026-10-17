#!/usr/bin/env python3
"""Conan recipe — pipebench 0.4 (Makefile, application).

pipebench measures the speed of stdin/stdout communication by sitting in the
middle of a pipe and passing data along. Single-file C program (pipebench.c)
with a raw Makefile (no configure, no test target).
"""

import json
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PipebenchConan(ConanFile):
    name = "pipebench"
    version = "0.4"
    description = "Measure the speed of stdin/stdout communication through a pipe"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ThomasHabets/pipebench"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # R33: compiler comes from Conan conf, never from bare shell env vars.
        # NOTE: tools.build:compiler_executables is a dict conf
        #   ({'c': '.../clang', 'cpp': '.../clang++'}); there is no
        #   'tools.build:compiler_executables:c' sub-conf, so conf.get()
        #   must read the whole dict first (sub-key lookup raises
        #   "does not exist in configuration list").
        compiler_exes = self.conf.get("tools.build:compiler_executables", default=None)
        cc = None
        if isinstance(compiler_exes, dict):
            cc = compiler_exes.get("c")
        cc = cc or os.environ.get("CC") or "clang"
        try:
            make = self.conf.get("user.hmbs:make_path", default="make", check_type=str) or "make"
        except Exception:
            make = "make"
        cflags = "-Wall -pedantic -O2"
        # Raw Makefile project (no configure, no check target). Upstream
        # default target `all: pipebench`; explicit `pipebench` target avoids
        # the `doc` rule (needs yodl2man). R9: always -j1.
        # NOTE: must run in source_folder where pipebench.c + Makefile live;
        # default build cwd is build-release, otherwise make reports
        # "No rule to make target 'pipebench'".
        self.run(f"\"{make}\" CC=\"{cc}\" CFLAGS=\"{cflags}\" -j1 pipebench",
                 cwd=self.source_folder)
        # Smoke check of the freshly built binary (same command the
        # test_package runs against the packaged binary).
        built_bin = os.path.join(self.source_folder, "pipebench")
        self.run(f"\"{built_bin}\" -h")
        # Upstream ships no test suite (single pipebench.c + Makefile without a
        # check/test target; see test_package/MANIFEST.yml audit). Emit the
        # no_tests marker so preflight evidence always has an upstream result.
        marker = {
            "status": "no_tests",
            "framework": "make",
            "command": "make CC=<cc> CFLAGS=<cflags> -j1 pipebench",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "pipebench 0.40 upstream has no test suite: no tests/ directory, no check/test target in Makefile, no ctest/gtest/pytest registration",
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))

    def package(self):
        copy(self, "pipebench", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "pipebench.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
