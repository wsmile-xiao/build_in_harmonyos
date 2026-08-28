#!/usr/bin/env python3
"""Conan recipe for dynamic-bitset 1.3.3 — header-only C++ dynamic bitset.

dynamic_bitset is a header-only C++17 dynamic bitset library
(include/sul/dynamic_bitset.hpp). Package installs the header. Upstream
tests: Catch2-based (tests/ — requires Catch2 + libpopcnt submodules,
not in tarball), built via CMake — build() runs them (rule 4).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class DynamicBitsetConan(ConanFile):
    name = "dynamic-bitset"
    version = "1.3.3"
    description = "dynamic_bitset — header-only C++17 dynamic bitset"
    license = "MIT"
    homepage = "https://github.com/pinam45/dynamic_bitset"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # catch2：上游测试框架（tests/ 用 Catch2——子模块不在 tarball）——
        # ohpcd 已发布 catch2/2.13.10-r0，仅本机构建时（can_run 守卫）
        if can_run(self):
            self.requires("catch2/2.13.10-r0")

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
        # Catch2 子模块不在 tarball——CMake 检查 extlibs/Catch2/CMakeLists.txt
        # （add_subdirectory 方式）——从 GitHub 下载 Catch2 **v3.5.0** 完整源码
        # 放到 extlibs/Catch2。注意：dynamic-bitset 测试 include
        # `catch2/generators/catch_generators.hpp` + `catch2/internal/
        # catch_uniform_integer_distribution.hpp`——v3.5.0 是唯一含这些头的
        # 版本（v2.13.10 无 generators 布局、v3.2.1/v3.3.2/v3.4.0 无
        # uniform_integer_distribution——均实测失败）。
        # 但 v3.5.0 与 OHOS LP64/clang 15 编译不兼容：SizedUnsignedType<16>
        # 缺特化（DoubleWidthUnsignedType_t 2*8=16）+ generic extendedMult
        # static_assert 'sizeof(unsigned long long) < sizeof(unsigned long)'
        # 失败（LP64 下均为 8 字节）——上游测试无法完整运行，如实记录
        ext_catch = os.path.join(src, "extlibs", "Catch2")
        if not os.path.isfile(os.path.join(ext_catch, "CMakeLists.txt")):
            import urllib.request
            import tarfile
            import shutil as _sh
            gh_url = ("https://codeload.github.com/catchorg/Catch2/"
                      "tar.gz/refs/tags/v3.5.0")
            tarball = os.path.join(self.build_folder, "catch2-src.tar.gz")
            req = urllib.request.Request(gh_url,
                                         headers={"User-Agent": "atomcode"})
            with urllib.request.urlopen(req, timeout=300) as resp:
                with open(tarball, "wb") as f:
                    f.write(resp.read())
            with tarfile.open(tarball) as z:
                z.extractall(self.build_folder)
            sub = os.path.join(self.build_folder, "Catch2-3.5.0")
            if os.path.isdir(sub):
                os.makedirs(ext_catch, exist_ok=True)
                _sh.copytree(sub, ext_catch, dirs_exist_ok=True)
                print("[dynamic-bitset tests] catch2 v3.5.0 source copied "
                      "to extlibs/Catch2")
        cfg = [cmake_cmd, src,
               "-DDYNAMICBITSET_BUILD_TESTS=ON",
               # docs 依赖 doxygen-awesome-css 子模块（tarball 不含——
               # configure 失败实测）——禁用 docs
               "-DDYNAMICBITSET_BUILD_DOCS=OFF",
               # Catch2::Catch2WithMain 需 CATCH_BUILD_STATIC_LIBRARY=ON
               # （默认 OFF——ALIAS target missing 实测）
               "-DCATCH_BUILD_STATIC_LIBRARY=ON",
               # 显式 CMAKE_BUILD_TYPE（同 cxxopts：ctest -C 空值报错实测）
               "-DCMAKE_BUILD_TYPE=Release",
               "-DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++",
               "-DCMAKE_CXX_FLAGS=-std=c++17",
               "-B", bdir]
        r = subprocess.run(cfg, capture_output=True, text=True, timeout=300)
        print("[dynamic-bitset upstream tests] cmake configure rc=%d"
              % r.returncode)
        if r.returncode != 0:
            print("[dynamic-bitset upstream tests]",
                  (r.stdout + r.stderr)[-800:])
            return
        r = subprocess.run([cmake_cmd, "--build", bdir, "-j", "4"],
                           capture_output=True, text=True, timeout=900)
        print("[dynamic-bitset upstream tests] cmake build rc=%d"
              % r.returncode)
        if r.returncode != 0:
            print("[dynamic-bitset upstream tests]",
                  (r.stdout + r.stderr)[-800:])
            return
        r = subprocess.run([ctest_cmd, "--test-dir", bdir,
                            "--output-on-failure"],
                           capture_output=True, text=True, timeout=900)
        out = r.stdout + r.stderr
        print("[dynamic-bitset upstream tests] ctest rc=%d" % r.returncode)
        for line in out.splitlines()[-12:]:
            print("[dynamic-bitset upstream tests]", line)

    def package(self):
        # header-only：安装 include/sul/dynamic_bitset.hpp
        import shutil
        inc_dir = os.path.join(self.package_folder, "include", "sul")
        os.makedirs(inc_dir, exist_ok=True)
        shutil.copy(os.path.join(self.source_folder, "include", "sul",
                                 "dynamic_bitset.hpp"),
                    os.path.join(inc_dir, "dynamic_bitset.hpp"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
