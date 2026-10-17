#!/usr/bin/env python3
"""Conan recipe for CLI11 2.7.2 — header-only C++ command line parser.

CLI11 is a header-only C++11 library for command line parsing. Package
installs the include/CLI/ headers (CLI.hpp umbrella + App/Option/...).
Upstream tests: Catch2-based unit tests (tests/*.cpp), built via CMake
CLI11_BUILD_TESTS — build() runs them for a real pass rate (rule 4).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class Cli11Conan(ConanFile):
    name = "cli11"
    version = "2.7.2"
    description = "CLI11 — command line parser for C++11 (header-only)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/CLIUtils/CLI11"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # catch2：上游测试框架（tests/ 用 Catch2——CMake 默认从 GitHub 下载
        # catch.hpp 超时实测）——ohpcd 已发布 catch2/2.13.10-r0（与 CLI11 期望
        # hash 3725c0f0 完全一致），仅本机构建时（can_run 守卫）
        if can_run(self):
            self.requires("catch2/2.13.10-r0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CLI11_BUILD_TESTS"] = "OFF"
        tc.variables["CLI11_BUILD_EXAMPLES"] = "OFF"
        tc.variables["CLI11_BUILD_DOCS"] = "OFF"
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
        # Catch2 依赖：从 conan 包拷贝 catch.hpp 到 CMake 期望的缓存位置
        # （tests/CMakeLists.txt 的 catch2_header 路径——hash 匹配则用缓存
        # 不再从 GitHub 下载——下载超时实测）
        catch2_pkg = next(
            (d.package_folder for d in self.dependencies.values()
             if d.ref.name == "catch2"), None)
        if catch2_pkg:
            import shutil
            catch_src = os.path.join(catch2_pkg, "include", "catch2",
                                     "catch.hpp")
            catch_dst = os.path.join(bdir, "tests", "catch2", "catch.hpp")
            if os.path.isfile(catch_src):
                os.makedirs(os.path.dirname(catch_dst), exist_ok=True)
                shutil.copy(catch_src, catch_dst)
                print("[cli11 tests] catch.hpp cached from conan pkg")
        # OHOS libc 缺 pthread_testcancel（AppTest.cpp:3162 编译失败实测——
        # 与 commoncpp2 同源）——写 stub 头 + -include 注入测试编译
        stub = os.path.join(self.build_folder, "pthread_stub.h")
        with open(stub, "w") as f:
            f.write("#ifndef PTHREAD_STUB_H\n#define PTHREAD_STUB_H\n"
                    "#include <pthread.h>\n"
                    "#ifndef pthread_testcancel\n"
                    "#define pthread_testcancel() ((void)0)\n#endif\n"
                    "#endif\n")
        cfg = [cmake_cmd, src,
               "-DCLI11_BUILD_TESTS=ON",
               "-DCLI11_BUILD_EXAMPLES=OFF",
               "-DCLI11_BUILD_DOCS=OFF",
               "-DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++",
               "-DCMAKE_CXX_FLAGS=-std=c++14 -include " + stub,
               "-B", bdir]
        r = subprocess.run(cfg, capture_output=True, text=True, timeout=300)
        print("[cli11 upstream tests] cmake configure rc=%d" % r.returncode)
        if r.returncode != 0:
            print("[cli11 upstream tests]", (r.stdout + r.stderr)[-800:])
            return
        r = subprocess.run([cmake_cmd, "--build", bdir, "-j", "4"],
                           capture_output=True, text=True, timeout=900)
        print("[cli11 upstream tests] cmake build rc=%d" % r.returncode)
        if r.returncode != 0:
            print("[cli11 upstream tests]", (r.stdout + r.stderr)[-800:])
            return
        r = subprocess.run([ctest_cmd, "--test-dir", bdir,
                            "--output-on-failure"],
                           capture_output=True, text=True, timeout=900)
        out = r.stdout + r.stderr
        print("[cli11 upstream tests] ctest rc=%d" % r.returncode)
        for line in out.splitlines()[-12:]:
            print("[cli11 upstream tests]", line)

    def package(self):
        # header-only：安装 include/CLI/ 头文件（CLI.hpp 伞头 + App/Option 等）
        import shutil
        shutil.copytree(os.path.join(self.source_folder, "include", "CLI"),
                        os.path.join(self.package_folder, "include", "CLI"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
