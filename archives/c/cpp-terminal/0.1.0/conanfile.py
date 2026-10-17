#!/usr/bin/env python3
"""Conan recipe for cpp-terminal 0.1.0 — header-only C++ terminal library.

cpp-terminal is a header-only C++ library for terminal manipulation
(cpp-terminal/terminal.h + terminal_base.h). Package installs the
headers. Upstream tests: doctest-based test_terminal.cpp + tests.sh
(examples/colors/keys) — build() runs them (rule 4).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class CppTerminalConan(ConanFile):
    name = "cpp-terminal"
    version = "0.1.0"
    description = "cpp-terminal — header-only C++ library for terminal manipulation"
    license = "MIT"
    homepage = "https://github.com/jupyter-xeus/cpp-terminal"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "OFF"
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
               "-DBUILD_TESTING=ON",
               # 显式 CMAKE_BUILD_TYPE（同 cxxopts：ctest -C 空值报错实测）
               "-DCMAKE_BUILD_TYPE=Release",
               "-DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++",
               "-DCMAKE_CXX_FLAGS=-std=c++11",
               "-B", bdir]
        r = subprocess.run(cfg, capture_output=True, text=True, timeout=300)
        print("[cpp-terminal upstream tests] cmake configure rc=%d"
              % r.returncode)
        if r.returncode != 0:
            print("[cpp-terminal upstream tests]", (r.stdout + r.stderr)[-800:])
            return
        r = subprocess.run([cmake_cmd, "--build", bdir, "-j", "4"],
                           capture_output=True, text=True, timeout=900)
        print("[cpp-terminal upstream tests] cmake build rc=%d" % r.returncode)
        if r.returncode != 0:
            print("[cpp-terminal upstream tests]", (r.stdout + r.stderr)[-800:])
            return
        r = subprocess.run([ctest_cmd, "--test-dir", bdir,
                            "--output-on-failure"],
                           capture_output=True, text=True, timeout=900)
        out = r.stdout + r.stderr
        print("[cpp-terminal upstream tests] ctest rc=%d" % r.returncode)
        for line in out.splitlines()[-12:]:
            print("[cpp-terminal upstream tests]", line)

    def package(self):
        # header-only：安装 cpp-terminal/ 头文件（terminal.h + terminal_base.h）
        import shutil
        shutil.copytree(os.path.join(self.source_folder, "cpp-terminal"),
                        os.path.join(self.package_folder, "include",
                                     "cpp-terminal"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
