#!/usr/bin/env python3
"""Conan recipe — utest 0.0-git20260928-df92c758 (header-only C/C++ test framework).

utest.h: a simple single-header unit testing framework for C/C++ with
colorful output, fixtures, parameterized and CRASH/EXPECT variants.
The package is pinned to official commit
df92c7589f7f1d1bd22489cc029e8a61ef538588 (2026-09-28).

Platform task: 开源鸿蒙PC专项积分赛-依赖 · utest 0.0-git20260928-df92c758 (自导入, 5 火种).

Build system note: the package installs only utest.h, but build() compiles
and executes the upstream CMake/CTest inventory. Settings keep all four keys (CI L0p gate requires
compiler/build_type even for header-only, fast-cpp-csv-parser
precedent).  R34 consumer verification compiles+runs a real test suite
against the installed header (test_package/test_utest.py).
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.build import can_run


class UtestConan(ConanFile):
    name = "utest"
    version = "0.0-git20260928-df92c758"
    description = "utest.h — single-header unit testing framework for C/C++"
    license = "Unlicense"
    homepage = "https://github.com/sheredom/utest.h"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # header-only,无编译产物——但 OHOS profile 要求 settings 含全部四项
    # (CI L0p 门禁实测:缺 compiler/build_type 构建失败,fast-cpp-csv-parser 先例)
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        for name in ("upstream_test.py", "native_compiler.py", "ohos_test_tmpfile.h"):
            copy(self, name, self.recipe_folder, self.export_sources_folder)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        if not can_run(self):
            raise RuntimeError("utest requires native execution of its upstream tests")
        compilers = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = compilers.get("c") or shutil.which("clang") or shutil.which("gcc")
        cxx = compilers.get("cpp") or shutil.which("clang++") or shutil.which("g++")
        if not cc or not cxx:
            raise RuntimeError("Both C and C++ compilers are required for upstream tests")
        command = [sys.executable, os.path.join(self.source_folder, "upstream_test.py"),
                   self.source_folder, os.path.join(self.build_folder, "upstream-tests"),
                   "--compiler", cc, "--cxx", cxx]
        if self.settings.os == "OHOS":
            command.append("--native-ohos")
        subprocess.run(command, check=True)

    def package(self):
        # header-only:安装 utest.h(单头文件)
        import shutil
        inc_dir = os.path.join(self.package_folder, "include")
        os.makedirs(inc_dir, exist_ok=True)
        shutil.copy(os.path.join(self.source_folder, "utest.h"),
                    os.path.join(inc_dir, "utest.h"))
        # 许可证:Unlicense(上游主许可)
        lic = os.path.join(self.source_folder, "LICENSE")
        if not os.path.isfile(lic):
            raise RuntimeError("Official upstream LICENSE missing")
        license_dir = os.path.join(self.package_folder, "licenses")
        os.makedirs(license_dir, exist_ok=True)
        shutil.copy(lic, os.path.join(license_dir, "LICENSE"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
