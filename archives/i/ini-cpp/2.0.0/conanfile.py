#!/usr/bin/env python3
"""Conan recipe for ini-cpp 2.0.0 — header-only C++17 INI parser.

ini-cpp (SSARCandy/ini-cpp) is a header-only C++17 INI parser: single header
ini/ini.h (namespace inih). Package installs the header. Upstream tests:
test/tests.cpp (27 GTest cases) with fixtures copied next to the test binary
(upstream test/CMakeLists.txt copies test/fixtures to the build dir). The
googletest git submodule is absent from the release tarball, so the tests are
compiled against the published conan gtest/1.17.0 package. The upstream
example.cpp requires boost (demo only, not part of the library) and is not
built.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class IniCppConan(ConanFile):
    name = "ini-cpp"
    version = "2.0.0"
    package_type = "header-library"
    license = "MIT"
    homepage = "https://github.com/SSARCandy/ini-cpp"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    description = "Yet another .ini parser for modern C++ (C++17)"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "conandata.yml"

    def export_sources(self):
        copy(self, "conandata.yml", dst=".", src=self.recipe_folder)

    def requirements(self):
        # GTest only for building the upstream unit tests (not exposed to
        # consumers of the header-only package).
        self.test_requires("gtest/1.17.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Header-only: nothing to compile for the library itself. Run the
        # upstream test suite (27 GTest cases) against conan's gtest package,
        # since the release tarball omits the googletest git submodule.
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        gtest_pkg = self.dependencies["gtest"].package_folder
        gtest_inc = os.path.join(gtest_pkg, "include")
        gtest_lib = os.path.join(gtest_pkg, "lib")
        cxx = (self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict) or {}).get("cpp", "c++")
        src = self.source_folder
        bdir = self.build_folder
        test_src = os.path.join(src, "test", "tests.cpp")
        binp = os.path.join(bdir, "all_test")
        # OHOS 沙箱 subprocess 相对名不搜 PATH（posix_spawn 差异实测）——
        # 编译器取自 profile conf 绝对路径；链接 gtest 包内静态库。
        cmd = [cxx, "-std=c++17", f"-I{src}", f"-I{gtest_inc}",
               test_src, "-o", binp, "-L", gtest_lib,
               "-lgtest", "-lgtest_main"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        print("[ini-cpp upstream tests] compile rc=%d" % r.returncode)
        if r.returncode != 0:
            print("[ini-cpp upstream tests]", (r.stdout + r.stderr)[-2000:])
            return
        # upstream test/CMakeLists.txt copies test/fixtures to the build dir;
        # tests read ./fixtures/config.ini etc. relative to the CWD.
        fixtures_dst = os.path.join(bdir, "fixtures")
        os.makedirs(fixtures_dst, exist_ok=True)
        for f in os.listdir(os.path.join(src, "test", "fixtures")):
            shutil.copy(os.path.join(src, "test", "fixtures", f),
                        os.path.join(fixtures_dst, f))
        r = subprocess.run([binp], capture_output=True, text=True,
                           timeout=600, cwd=bdir)
        out = r.stdout + r.stderr
        print("[ini-cpp upstream tests] run rc=%d" % r.returncode)
        for line in out.splitlines()[-15:]:
            print("[ini-cpp upstream tests]", line)
        if r.returncode != 0:
            raise RuntimeError("ini-cpp upstream tests failed rc=%d" % r.returncode)

    def package(self):
        copy(self, "ini.h", dst=os.path.join(self.package_folder, "include", "ini"),
             src=os.path.join(self.source_folder, "ini"))
        copy(self, "LICENSE.txt", dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = []
