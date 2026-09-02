#!/usr/bin/env python3
"""Conan recipe for lyra 1.8.0 — header-only C++11 command line parser.

Lyra is a header-only C++11 library for command line parsing (bfgroup/Lyra).
Package installs the include/lyra/ headers (lyra.hpp umbrella + detail/*).
Upstream tests: standalone *_run_test.cpp executables built with clang++
(mini_test.hpp harness) — build() compiles and runs them for a real pass
rate; base_compile_test.cpp is compile-only (no main) and issue_93_test.cpp
requires C++14 (std::make_unique).
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import (apply_conandata_patches,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class LyraConan(ConanFile):
    name = "lyra"
    version = "1.8.0"
    description = "lyra — a simple to use, composing, header only, command line arguments parser for C++ 11 and beyond"
    license = "BSL-1.0"
    homepage = "https://github.com/bfgroup/Lyra"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # header-only——无需编译库本身；直接跑上游测试（实测回填）
        if can_run(self):
            self._run_upstream_tests()

    def _run_upstream_tests(self):
        src = self.source_folder
        tests_dir = os.path.join(src, "tests")
        if not os.path.isdir(tests_dir):
            print("[lyra upstream tests] tests dir missing, skipped")
            return
        import tempfile
        out = tempfile.mkdtemp(prefix="lyra-tests-")
        clang = "/data/service/hnp/bin/clang++"
        inc = os.path.join(src, "include")
        # tests/*_run_test.cpp include doc_*.cpp / example sources from the
        # examples/ dir (e.g. "doc_commands.cpp") — so add it to include path
        exdir = os.path.join(src, "examples")
        inc_args = [f"-I{inc}"]
        if os.path.isdir(exdir):
            inc_args.append(f"-I{exdir}")
        passed, failed = 0, 0
        failed_list = []
        for f in sorted(os.listdir(tests_dir)):
            if not (f.endswith("_test.cpp")):
                continue
            fpath = os.path.join(tests_dir, f)
            binary = os.path.join(out, f[:-4])
            std = "c++14" if f == "issue_93_test.cpp" else "c++11"
            r = subprocess.run([clang, f"-std={std}", *inc_args,
                                "-o", binary, fpath],
                               capture_output=True, text=True, timeout=180)
            if r.returncode != 0:
                # base_compile_test.cpp has no main: compile-only check
                if f == "base_compile_test.cpp":
                    rc = subprocess.run([clang, f"-std={std}", *inc_args,
                                         "-c", fpath, "-o", binary + ".o"],
                                        capture_output=True, text=True)
                    if rc.returncode == 0:
                        passed += 1
                        continue
                failed += 1
                failed_list.append(f)
                print(f"[lyra upstream tests] BUILD FAIL {f}: "
                      f"{(r.stderr or '')[-400:]}")
                continue
            r = subprocess.run([binary], capture_output=True, text=True,
                               timeout=120)
            if r.returncode == 0:
                passed += 1
            else:
                failed += 1
                failed_list.append(f)
                print(f"[lyra upstream tests] RUN FAIL {f}: "
                      f"{(r.stdout + r.stderr)[-400:]}")
        import shutil
        shutil.rmtree(out, ignore_errors=True)
        print(f"[lyra upstream tests] {passed} passed / {failed} failed")
        if failed_list:
            print(f"[lyra upstream tests] failed: {failed_list}")

    def package(self):
        # header-only：安装 include/lyra/ 头文件（lyra.hpp 伞头 + detail/ 等）
        import shutil
        shutil.copytree(os.path.join(self.source_folder, "include", "lyra"),
                        os.path.join(self.package_folder, "include", "lyra"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "lyra")
        self.cpp_info.set_property("cmake_target_name", "lyra::lyra")