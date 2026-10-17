#!/usr/bin/env python3
"""Conan recipe for rapidcsv 9.07 — header-only C++ CSV parser.

rapidcsv is a header-only C++11 library for CSV parsing
(src/rapidcsv.h). Package installs the header. Upstream tests: custom
unittest framework (tests/unittest.h, test00X.cpp), built via CMake
RAPIDCSV_BUILD_TESTS — build() runs them (rule 4).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class RapidcsvConan(ConanFile):
    name = "rapidcsv"
    version = "9.07"
    description = "rapidcsv — C++11 CSV parser library (header-only)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/d99kris/rapidcsv"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["RAPIDCSV_BUILD_TESTS"] = "OFF"
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
               "-DRAPIDCSV_BUILD_TESTS=ON",
               # 必须 Debug：上游 add_unit_test 宏只在 CMAKE_BUILD_TYPE=Debug
               # 注册（test001~test110 单元测试），Release 只注册 2 个 perf
               # 测试（N=2 少报实测）——Debug 全量 112 用例
               "-DCMAKE_BUILD_TYPE=Debug",
               "-DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++",
               "-DCMAKE_CXX_FLAGS=-std=c++11",
               "-B", bdir]
        r = subprocess.run(cfg, capture_output=True, text=True, timeout=300)
        print("[rapidcsv upstream tests] cmake configure rc=%d" % r.returncode)
        if r.returncode != 0:
            print("[rapidcsv upstream tests]", (r.stdout + r.stderr)[-800:])
            return
        r = subprocess.run([cmake_cmd, "--build", bdir, "-j", "4"],
                           capture_output=True, text=True, timeout=900)
        print("[rapidcsv upstream tests] cmake build rc=%d" % r.returncode)
        if r.returncode != 0:
            print("[rapidcsv upstream tests]", (r.stdout + r.stderr)[-800:])
            return
        # ptest001/002 读 '../tests/msft.csv'（相对 ctest 工作目录 build-tests
        # → build/Release/tests/msft.csv 不存在——ios_base::clear 失败实测）——
        # 把源码 tests/*.csv 样本拷贝到该相对位置
        import shutil, glob
        rel_tests = os.path.join(os.path.dirname(bdir), "tests")
        os.makedirs(rel_tests, exist_ok=True)
        for csv in glob.glob(os.path.join(src, "tests", "*.csv")):
            shutil.copy(csv, os.path.join(rel_tests, os.path.basename(csv)))
        print("[rapidcsv tests] copied csv samples to %s" % rel_tests)
        r = subprocess.run([ctest_cmd, "--test-dir", bdir,
                            "--output-on-failure"],
                           capture_output=True, text=True, timeout=900)
        out = r.stdout + r.stderr
        print("[rapidcsv upstream tests] ctest rc=%d" % r.returncode)
        for line in out.splitlines()[-12:]:
            print("[rapidcsv upstream tests]", line)

    def package(self):
        # header-only：安装 src/rapidcsv.h（单头文件）
        import shutil
        inc_dir = os.path.join(self.package_folder, "include")
        os.makedirs(inc_dir, exist_ok=True)
        shutil.copy(os.path.join(self.source_folder, "src", "rapidcsv.h"),
                    os.path.join(inc_dir, "rapidcsv.h"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
