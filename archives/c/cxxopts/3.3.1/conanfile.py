#!/usr/bin/env python3
"""Conan recipe for cxxopts 3.3.1 — header-only C++ command line parser.

cxxopts is a header-only C++11/14 library for command line parsing
(single header cxxopts.hpp). Package installs the header. Upstream tests:
Catch2-based (test/ dir ships its own catch.hpp — no network needed),
built via CMake CXXOPTS_BUILD_TESTS — build() runs them (rule 4).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class CxxoptsConan(ConanFile):
    name = "cxxopts"
    version = "3.3.1"
    description = "cxxopts — lightweight C++ command line option parser (header-only)"
    license = "MIT"
    homepage = "https://github.com/jarro2783/cxxopts"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CXXOPTS_BUILD_TESTS"] = "OFF"
        tc.variables["CXXOPTS_BUILD_EXAMPLES"] = "OFF"
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
               "-DCXXOPTS_BUILD_TESTS=ON",
               "-DCXXOPTS_BUILD_EXAMPLES=OFF",
               # 必须显式 CMAKE_BUILD_TYPE——test/CMakeLists.txt 的 ctest
               # -C ${CMAKE_BUILD_TYPE} 为空报 'Invalid value used with -C'
               # （find-package-test/add-subdirectory-test 失败实测）
               "-DCMAKE_BUILD_TYPE=Release",
               "-DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++",
               "-DCMAKE_CXX_FLAGS=-std=c++14",
               "-B", bdir]
        r = subprocess.run(cfg, capture_output=True, text=True, timeout=300)
        print("[cxxopts upstream tests] cmake configure rc=%d" % r.returncode)
        if r.returncode != 0:
            print("[cxxopts upstream tests]", (r.stdout + r.stderr)[-800:])
            return
        r = subprocess.run([cmake_cmd, "--build", bdir, "-j", "4"],
                           capture_output=True, text=True, timeout=900)
        print("[cxxopts upstream tests] cmake build rc=%d" % r.returncode)
        if r.returncode != 0:
            print("[cxxopts upstream tests]", (r.stdout + r.stderr)[-800:])
            return
        r = subprocess.run([ctest_cmd, "--test-dir", bdir,
                            "--output-on-failure"],
                           capture_output=True, text=True, timeout=900)
        out = r.stdout + r.stderr
        print("[cxxopts upstream tests] ctest rc=%d" % r.returncode)
        for line in out.splitlines()[-12:]:
            print("[cxxopts upstream tests]", line)

    def package(self):
        # header-only：安装 include/cxxopts.hpp（单头文件）
        import shutil
        inc_dir = os.path.join(self.package_folder, "include")
        os.makedirs(inc_dir, exist_ok=True)
        shutil.copy(os.path.join(self.source_folder, "include",
                                 "cxxopts.hpp"),
                    os.path.join(inc_dir, "cxxopts.hpp"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
