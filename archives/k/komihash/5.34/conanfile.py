#!/usr/bin/env python3
"""Conan recipe — komihash 5.34 (single-header ISO C99 hash library)."""

import json
import os
import shlex
import subprocess

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class KomihashConan(ConanFile):
    name = "komihash"
    version = "5.34"
    description = (
        "Fast 64-bit komihash hash function, komirand PRNG, and streamed "
        "hashing in a single ISO C99 header"
    )
    license = "MIT"
    homepage = "https://github.com/avaneev/komihash"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Upstream ships one vector program (testvec.c) and no build system;
        # compile and run it with the OHOS profile compiler (E307 pattern).
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cc = compiler_executables.get("c", "clang")
        src = self.source_folder
        testbin = os.path.join(self.build_folder, "testvec")
        compile_cmd = (
            f"{shlex.quote(cc)} -O2 -std=c99 -I{shlex.quote(src)} "
            f"{shlex.quote(os.path.join(src, 'testvec.c'))} "
            f"-o {shlex.quote(testbin)}"
        )
        self.run(compile_cmd)
        self._run_upstream_tests(testbin)

    def _run_upstream_tests(self, testbin):
        proc = subprocess.run(
            [testbin],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
        if proc.returncode != 0:
            self.output.error(proc.stdout[-2000:])
            raise RuntimeError("upstream test failed: testvec (non-zero exit)")
        # testvec prints vectors without asserting; verify the full output
        # structure: 3 seeds x (5 string vectors + 17 bulk vectors) plus
        # 3 komirand sections.
        lines = proc.stdout.splitlines()
        seed_lines = sum(1 for ln in lines if ln.startswith("komihash UseSeed"))
        string_lines = sum(
            1 for ln in lines if ln.startswith('"') and "= 0x" in ln)
        bulk_lines = sum(1 for ln in lines if ln.startswith("bulk("))
        rand_lines = sum(
            1 for ln in lines if ln.startswith("komirand Seed1/Seed2"))
        if (seed_lines, string_lines, bulk_lines, rand_lines) != (3, 15, 51, 3):
            raise RuntimeError(
                "upstream testvec output incomplete: "
                f"seeds={seed_lines} strings={string_lines} "
                f"bulks={bulk_lines} rand_sections={rand_lines}")
        result = {
            "status": "passed",
            "framework": "direct-compile-program",
            "command": "clang -O2 -std=c99 testvec.c && ./testvec",
            "discovered": 1,
            "executed": 1,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
            "detail": (
                "1 upstream vector program executed: 3 seeds x (5 strings + "
                "17 bulk lengths) komihash vectors + 3 x 12 komirand outputs "
                "printed in full"),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))

    def package(self):
        copy(self, "komihash.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "komihash")
        self.cpp_info.set_property("cmake_target_name", "komihash::komihash")
