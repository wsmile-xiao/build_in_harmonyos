#!/usr/bin/env python3
"""Conan recipe — pcg-cpp 0.98 (header-only C++11 RNG family, Makefile-driven tests)."""

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


class PcgCppConan(ConanFile):
    name = "pcg-cpp"
    version = "0.98"
    description = (
        "PCG random number generation for C++ — header-only family of "
        "pseudo-random number generators"
    )
    license = "Apache-2.0"
    homepage = "https://www.pcg-random.org"
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
        # Upstream test-high/ registers 42 check-* programs (Makefile
        # TARGETS). run-tests.sh executes 41 of them: 40 runs are compared
        # against expected/ golden outputs; check-pcg64_unique runs once
        # with its output discarded (/dev/null); check-pcg32_unique is
        # never invoked by the upstream script. The script itself always
        # exits 0, so pass/fail is judged by re-running the diff here
        # (mechanical exit-code criterion).
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compiler_executables.get("cpp", "clang++")
        test_dir = os.path.join(self.source_folder, "test-high")
        make_cmd = (
            f"make -C {shlex.quote(test_dir)} -j1 "
            f"CXX={shlex.quote(cxx)} "
            f"CPPFLAGS={shlex.quote('-I../include')} "
            f"CXXFLAGS={shlex.quote('-std=c++11 -O1')}"
        )
        self.run(make_cmd)
        self._run_upstream_tests(test_dir)

    def _run_upstream_tests(self, test_dir):
        subprocess.run(
            ["sh", "run-tests.sh"],
            cwd=test_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=600,
            check=True,
        )
        # Mechanical verdict: byte-compare every golden output against the
        # actual run in Python. run-tests.sh cannot be trusted by exit code
        # (see comment in build()), and external `diff` is not portable —
        # busybox diff on CI workers rejects `diff -x`.
        golden_dir = os.path.join(test_dir, "expected")
        actual_dir = os.path.join(test_dir, "actual")
        golden_files = sorted(f for f in os.listdir(golden_dir)
                              if f.endswith(".out"))
        mismatches = []
        for name in golden_files:
            apath = os.path.join(actual_dir, name)
            if not os.path.exists(apath):
                mismatches.append(f"missing actual output: {name}")
                continue
            with open(os.path.join(golden_dir, name), "rb") as gf:
                golden = gf.read()
            with open(apath, "rb") as af:
                actual = af.read()
            if golden != actual:
                mismatches.append(f"content mismatch: {name}")
        out_files = len([f for f in os.listdir(actual_dir)
                         if f.endswith(".out")])
        if mismatches or out_files != len(golden_files):
            detail = "; ".join(mismatches[:5]) or (
                f"actual .out count {out_files} != golden {len(golden_files)}")
            self.output.error(detail)
            raise RuntimeError(
                "upstream test failed: golden mismatch in test-high: "
                + detail)
        result = {
            "status": "passed",
            "framework": "makefile-programs",
            "command": (
                "make -C test-high -j1 CXX=<profile cpp> "
                "CPPFLAGS=-I../include CXXFLAGS='-std=c++11 -O1'; "
                "sh run-tests.sh; python byte-compare expected/ vs actual/"),
            "discovered": 42,
            "compiled": 42,
            "executed": 41,
            "passed": 40,
            "failed": 0,
            "skipped": 1,
            "detail": (
                "42 upstream check-* targets compiled; run-tests.sh "
                "executed 41 (40 golden outputs byte-compared + "
                "check-pcg64_unique smoke with output discarded); "
                "check-pcg32_unique skipped: never invoked by upstream "
                "run-tests.sh"),
        }
        if len(golden_files) != 40:
            raise RuntimeError(
                f"unexpected golden output count: {len(golden_files)} != 40")
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))

    def package(self):
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "pcg-cpp")
        self.cpp_info.set_property("cmake_target_name", "pcg-cpp::pcg-cpp")
