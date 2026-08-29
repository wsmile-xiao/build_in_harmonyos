#!/usr/bin/env python3
"""Conan recipe for vc 1.4.5 — header-only SIMD Vector Classes for C++.

Vc is a free, portable, fast and concise SIMD vectorization library
(header-only). No compilation of the library itself — package installs the
Vc/ headers. Upstream tests build via CMake BUILD_TESTING (unittest-based,
ctest) — build() runs them for a real pass rate (rule 4).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class VcConan(ConanFile):
    name = "vc"
    version = "1.4.5"
    description = "Vc — SIMD Vector Classes for C++ (header-only)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/VcDevel/Vc"
    url = ""

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游测试（rule 4 实测回填）：BUILD_TESTING=ON 单独构建 tests 并
        # 跑 ctest 拿真实通过率（头文件库——打包产物与测试同源）
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        import subprocess
        import sys

        bdir = os.path.join(self.build_folder, "build-tests")
        os.makedirs(bdir, exist_ok=True)
        src = self.source_folder
        # 上游测试依赖 git 子模块（tests/virtest + tests/testdata——tarball
        # 不含，virtest/vir/test.h 缺失实测）——从 GitHub 下载子模块内容
        self._fetch_submodules()
        # OHOS 沙箱 subprocess 相对名不搜 PATH（posix_spawn 差异实测——与
        # rich 同源）——cmake/ctest 用绝对路径（/data/service/hnp/bin 下）
        cmake_cmd = "/data/service/hnp/bin/cmake"
        ctest_cmd = "/data/service/hnp/bin/ctest"
        cfg = [cmake_cmd, src,
               "-DBUILD_TESTING=ON", "-DBUILD_EXAMPLES=OFF",
               "-DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++",
               "-DCMAKE_CXX_FLAGS=-std=c++14 -DVc_IMPL=Scalar",
               "-B", bdir]
        r = subprocess.run(cfg, capture_output=True, text=True)
        print("[vc upstream tests] cmake configure rc=%d" % r.returncode)
        if r.returncode != 0:
            print("[vc upstream tests]", (r.stdout + r.stderr)[-800:])
            return
        r = subprocess.run([cmake_cmd, "--build", bdir, "-j", "4"],
                           capture_output=True, text=True)
        print("[vc upstream tests] cmake build rc=%d" % r.returncode)
        if r.returncode != 0:
            print("[vc upstream tests]", (r.stdout + r.stderr)[-800:])
            return
        # 运行 ctest（全部用例——通过率分母为全部测试）
        r = subprocess.run([ctest_cmd, "--test-dir", bdir,
                            "--output-on-failure"],
                           capture_output=True, text=True, timeout=900)
        out = r.stdout + r.stderr
        print("[vc upstream tests] ctest rc=%d" % r.returncode)
        for line in out.splitlines()[-12:]:
            print("[vc upstream tests]", line)

    def _fetch_submodules(self):
        import urllib.request
        import tarfile
        import shutil
        import time

        def _dl(url, path, tries=3, timeout=300):
            for i in range(tries):
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "atomcode"})
                    with urllib.request.urlopen(req, timeout=timeout) as r:
                        data = r.read()
                    with open(path, "wb") as f:
                        f.write(data)
                    return len(data)
                except Exception as e:
                    print("[vc submodule] try%d FAIL: %s" % (i + 1, e))
                    time.sleep(3)
            return 0

        tests_dir = os.path.join(self.source_folder, "tests")
        # virtest（unittest 框架）——用 codeload 端点（github.com/archive
        # 端点 RemoteDisconnected 实测——rich 同源教训）+ 重试
        vdir = os.path.join(tests_dir, "virtest")
        if not os.path.isdir(os.path.join(vdir, "vir")):
            url = ("https://codeload.github.com/mattkretz/virtest/"
                   "tar.gz/refs/heads/master")
            t = os.path.join(self.build_folder, "virtest-master.tar.gz")
            n = _dl(url, t)
            if n and tarfile.is_tarfile(t):
                with tarfile.open(t) as z:
                    z.extractall(self.build_folder)
                sub = os.path.join(self.build_folder, "virtest-master")
                if os.path.isdir(sub):
                    os.makedirs(vdir, exist_ok=True)
                    shutil.copytree(sub, vdir, dirs_exist_ok=True)
        # testdata（测试样本）——完整 tarball 272MB（raw.githubusercontent
        # 按需下载超时实测——codeload 端点可用）——整包下载解压
        tdir = os.path.join(tests_dir, "testdata")
        if not os.path.isdir(tdir) or not os.listdir(tdir):
            url = ("https://codeload.github.com/VcDevel/vc-testdata/"
                   "tar.gz/refs/heads/master")
            t = os.path.join(self.build_folder, "vc-testdata.tar.gz")
            n = _dl(url, t, tries=3, timeout=300)
            if n and tarfile.is_tarfile(t):
                with tarfile.open(t) as z:
                    z.extractall(self.build_folder)
                sub = os.path.join(self.build_folder, "vc-testdata-master")
                if os.path.isdir(sub):
                    os.makedirs(tdir, exist_ok=True)
                    shutil.copytree(sub, tdir, dirs_exist_ok=True)
            else:
                print("[vc submodule] WARN: vc-testdata download failed")

    def package(self):
        # header-only + 静态库 libVc.a（CMake 构建 src/support_dummy.cpp +
        # src/const.cpp——smoke 需链接 checkLibraryAbi 实测）
        import shutil
        shutil.copytree(os.path.join(self.source_folder, "Vc"),
                        os.path.join(self.package_folder, "include", "Vc"))
        # 部分配置头（config.h）由 CMake 生成——拷贝生成物
        gen = os.path.join(self.build_folder, "Vc", "config.h")
        if os.path.isfile(gen):
            shutil.copy(gen, os.path.join(self.package_folder, "include",
                                          "Vc", "config.h"))
        # 静态库 libVc.a
        libdir = os.path.join(self.package_folder, "lib")
        os.makedirs(libdir, exist_ok=True)
        for root, _dirs, files in os.walk(self.build_folder):
            for f in files:
                if f == "libVc.a":
                    shutil.copy(os.path.join(root, f),
                                os.path.join(libdir, f))

    def package_info(self):
        self.cpp_info.libs = ["Vc"]
        self.cpp_info.includedirs = ["include"]
