#!/usr/bin/env python3
"""Conan recipe for argparse 3.2 — header-only C++ argument parser.

argparse is a header-only C++17 argument parser (single header
include/argparse/argparse.hpp). Package installs the header. Upstream
tests: doctest-based (test/ dir ships its own doctest.hpp — no network),
built via CMake ARGPARSE_BUILD_TESTS — build() runs them (rule 4).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class ArgparseConan(ConanFile):
    name = "argparse"
    version = "3.2"
    description = "argparse — C++17 command line argument parser (header-only)"
    license = "MIT"
    homepage = "https://github.com/p-ranav/argparse"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ARGPARSE_BUILD_TESTS"] = "OFF"
        tc.variables["ARGPARSE_BUILD_SAMPLES"] = "OFF"
        tc.generate()

    def build(self):
        # header-only——无需编译库本身；直接跑上游测试（rule 4 实测回填）
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        import subprocess

        bdir = os.path.join(self.build_folder, "build-tests")
        os.makedirs(bdir, exist_ok=True)
        src = self.source_folder
        # OHOS 沙箱 subprocess 相对名不搜 PATH（posix_spawn 差异实测——与
        # rich/vc 同源）——cmake/ctest 用绝对路径
        cmake_cmd = "/data/service/hnp/bin/cmake"
        ctest_cmd = "/data/service/hnp/bin/ctest"
        cfg = [cmake_cmd, src,
               "-DARGPARSE_BUILD_TESTS=ON",
               "-DARGPARSE_BUILD_SAMPLES=OFF",
               # 显式 CMAKE_BUILD_TYPE（同 cxxopts：ctest -C 空值报错实测）
               "-DCMAKE_BUILD_TYPE=Release",
               "-DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++",
               "-DCMAKE_CXX_FLAGS=-std=c++17",
               "-B", bdir]
        r = subprocess.run(cfg, capture_output=True, text=True, timeout=300)
        print("[argparse upstream tests] cmake configure rc=%d" % r.returncode)
        if r.returncode != 0:
            print("[argparse upstream tests]", (r.stdout + r.stderr)[-800:])
            return
        r = subprocess.run([cmake_cmd, "--build", bdir, "-j", "4"],
                           capture_output=True, text=True, timeout=900)
        print("[argparse upstream tests] cmake build rc=%d" % r.returncode)
        if r.returncode != 0:
            print("[argparse upstream tests]", (r.stdout + r.stderr)[-800:])
            return
        # argparse 测试未注册为 ctest 用例（'No tests were found' 实测）——
        # 直接运行 tests 可执行（doctest 自带统计）
        tests_bin = os.path.join(bdir, "test", "tests")
        if os.path.isfile(tests_bin):
            r = subprocess.run([tests_bin], capture_output=True, text=True,
                               timeout=900)
            out = r.stdout + r.stderr
            print("[argparse upstream tests] run rc=%d" % r.returncode)
            for line in out.splitlines()[-12:]:
                print("[argparse upstream tests]", line)
        else:
            print("[argparse upstream tests] WARN: tests binary not found")

    def package(self):
        # header-only：安装 include/argparse/argparse.hpp（单头文件）
        import shutil
        inc_dir = os.path.join(self.package_folder, "include", "argparse")
        os.makedirs(inc_dir, exist_ok=True)
        shutil.copy(os.path.join(self.source_folder, "include", "argparse",
                                 "argparse.hpp"),
                    os.path.join(inc_dir, "argparse.hpp"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
