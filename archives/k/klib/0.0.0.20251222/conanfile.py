#!/usr/bin/env python3
"""Conan recipe — klib 0.0.0.20251222 snapshot (Makefile)."""

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


class KlibConan(ConanFile):
    name = "klib"
    version = "0.0.0.20251222"
    description = "Standalone and lightweight generic C library"
    license = "MIT"
    homepage = "https://github.com/attractivechaos/klib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1.1", transitive_headers=True,
                      transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cc = compiler_executables.get("c", "clang")
        cxx = compiler_executables.get("cpp", "clang++")
        zlib = self.dependencies["zlib"].cpp_info
        include_flags = " ".join(
            f"-I{shlex.quote(path)}" for path in zlib.includedirs)
        lib_flags = " ".join(
            f"-L{shlex.quote(path)}" for path in zlib.libdirs)
        cflags = f"-O2 -Wall -I.. -U__linux__ -include stdint.h {include_flags}"
        ldflags = lib_flags
        test_dir = os.path.join(self.source_folder, "test")
        command = (
            f"make -C {shlex.quote(test_dir)} -j1 all "
            f"kthread_test ketopt_test kbarena_test "
            f"CC={shlex.quote(cc)} CXX={shlex.quote(cxx)} "
            f"CFLAGS={shlex.quote(cflags)} CXXFLAGS={shlex.quote(cflags)} "
            f"LDFLAGS={shlex.quote(ldflags)}"
        )
        self.run(command)
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        test_dir = os.path.join(self.source_folder, "test")
        checks = [
            ("kbtree_test", ["1000"]),
            ("khash_keith", ["1000"]),
            ("khash_keith2", ["1"]),
            ("khash_test", ["1000"]),
            ("klist_test", []),
            ("kseq_test", ["kseq_test.dat"]),
            ("kseq_bench", ["kseq_test.dat"]),
            ("kseq_bench2", ["kseq_test.dat"]),
            ("ksort_test", ["1000"]),
            ("ksort_test-stl", ["1000"]),
            ("kvec_test", []),
            ("kmin_test", []),
            ("kstring_bench", []),
            ("kstring_bench2", []),
            ("kstring_test", []),
            ("kavl_test", []),
            ("kavl-lite_test", []),
            ("kthread_test", ["2"]),
            ("kthread_test2", ["kseq_test.dat", "2", "2"]),
            ("ketopt_test", ["--foo", "--bar=1", "arg1"]),
            ("kbarena_test", []),
        ]
        passed = 0
        for executable, args in checks:
            proc = subprocess.run(
                [os.path.join(test_dir, executable), *args],
                cwd=test_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=300,
            )
            if proc.returncode != 0:
                self.output.error(proc.stdout[-2000:])
                raise RuntimeError(f"upstream test failed: {executable}")
            passed += 1
        result = {
            "status": "passed",
            "framework": "makefile-programs",
            "command": "make -C test all kthread_test ketopt_test kbarena_test; run 21 upstream programs",
            "discovered": 21,
            "executed": passed,
            "passed": passed,
            "failed": 0,
            "skipped": 21 - passed,
            "detail": "21 upstream targets compiled and executed",
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))

    def package(self):
        copy(self, "*.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include", "klib"),
             keep_path=False)
        copy(self, "*.c", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include", "klib"),
             keep_path=False)
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "cpp"),
             dst=os.path.join(self.package_folder, "include", "klib", "cpp"),
             keep_path=False)
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "klib")
        self.cpp_info.set_property("cmake_target_name", "klib::klib")
