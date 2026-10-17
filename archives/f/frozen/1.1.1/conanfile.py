#!/usr/bin/env python3
"""Conan recipe for frozen 1.1.1 — header-only C++ constexpr containers.

frozen is a header-only C++14 library of constexpr containers
(include/frozen/ — map/set/unordered_map/string/algorithm). Package
installs the headers. Upstream tests: Catch2-based (tests/ ships
catch.hpp — no network), built via CMake — build() runs them (rule 4).

1.1.1 差异（相对 1.2.0）：测试开关为 `frozen.tests`（CMAKE_DEPENDENT_OPTION，
1.2.0 才改名 FROZEN_BUILD_TEST）；开启后同时构建 tests/ 与 examples/。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.errors import ConanException


class FrozenConan(ConanFile):
    name = "frozen"
    version = "1.1.1"
    description = "frozen — header-only C++14 constexpr containers"
    license = "Apache-2.0"
    homepage = "https://github.com/serge-sans-paille/frozen"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        CMakeToolchain(self).generate()

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
               # 1.1.1 测试开关：frozen.tests（CMAKE_DEPENDENT_OPTION，
               # 条件 NOT subproject——本配置为顶层工程，条件成立）
               "-Dfrozen.tests=ON",
               # 显式 CMAKE_BUILD_TYPE（同 cxxopts：ctest -C 空值报错实测）
               "-DCMAKE_BUILD_TYPE=Release",
               "-DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++",
               "-DCMAKE_CXX_FLAGS=-std=c++14",
               "-B", bdir]
        r = subprocess.run(cfg, capture_output=True, text=True, timeout=300)
        print("[frozen upstream tests] cmake configure rc=%d" % r.returncode)
        if r.returncode != 0:
            print("[frozen upstream tests]", (r.stdout + r.stderr)[-800:])
            raise ConanException("frozen 1.1.1 upstream tests cmake configure failed")
        r = subprocess.run([cmake_cmd, "--build", bdir, "-j", "4"],
                           capture_output=True, text=True, timeout=900)
        print("[frozen upstream tests] cmake build rc=%d" % r.returncode)
        if r.returncode != 0:
            print("[frozen upstream tests]", (r.stdout + r.stderr)[-800:])
            raise ConanException("frozen 1.1.1 upstream tests build failed")
        r = subprocess.run([ctest_cmd, "--test-dir", bdir,
                            "--output-on-failure"],
                           capture_output=True, text=True, timeout=900)
        out = r.stdout + r.stderr
        print("[frozen upstream tests] ctest rc=%d" % r.returncode)
        for line in out.splitlines()[-12:]:
            print("[frozen upstream tests]", line)
        if r.returncode != 0:
            raise ConanException("frozen 1.1.1 upstream ctest failed")

    def package(self):
        # header-only：安装 include/frozen/ 头文件目录（map/set/unordered 等）
        import shutil
        shutil.copytree(os.path.join(self.source_folder, "include",
                                     "frozen"),
                        os.path.join(self.package_folder, "include",
                                     "frozen"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
