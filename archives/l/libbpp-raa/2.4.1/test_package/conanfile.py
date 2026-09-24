#!/usr/bin/env python3
"""Conan test_package — libbpp-raa 2.4.1（消费者视角）。

编译并运行 test_bpp_raa.cpp（3 项断言：RaaList 三个静态常量 + 默认构造）。
RAA 是数据库驱动库，无数据库时无法做更多行为级断言 —— 本测试验证的是
「消费者能正确链接被测包及其 bpp-seq / bpp-core / zlib 依赖、公开符号可解析」。
链接策略：按绝对路径链 4 个静态归档，消费者零运行期 .so 依赖。
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibbppRaaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _folder(self, name):
        try:
            dep = self.dependencies[name]
            return getattr(dep, "package_folder", None)
        except Exception:
            return None

    def generate(self):
        tc = CMakeToolchain(self)
        for var, name in (("LIBBPP_RAA_PACKAGE_FOLDER", "libbpp-raa"),
                          ("LIBBPP_SEQ_PACKAGE_FOLDER", "libbpp-seq"),
                          ("ZLIB_PACKAGE_FOLDER", "zlib")):
            folder = self._folder(name)
            if folder:
                tc.cache_variables[var] = folder.replace("\\", "/")
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _ctest_bin(self):
        found = shutil.which("ctest")
        if found:
            return found
        for c in ("/data/service/hnp/bin/ctest",
                  "/usr/local/bin/ctest", "/usr/bin/ctest"):
            if os.path.isfile(c):
                return c
        return "ctest"

    def test(self):
        discovered = 3
        if not can_run(self):
            self.output.info("cross build: packaged binary cannot run on the build host")
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
                "executed": False, "passed": False,
                "command": "ctest -R test_bpp_raa",
                "discovered": discovered, "passedCount": 0,
            }, ensure_ascii=False))
            return
        ctest_bin = self._ctest_bin()
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        argv = ([bash, "-c", f"{ctest_bin} -V --output-on-failure -R test_bpp_raa"]
                if os.path.isfile(bash)
                else [ctest_bin, "-V", "--output-on-failure", "-R", "test_bpp_raa"])
        proc = subprocess.run(argv, cwd=self.build_folder, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, timeout=600)
        output = proc.stdout or ""
        self.output.info(output[-2000:])
        passed_count = len(re.findall(r"CHECK OK \d+/3", output))
        passed = proc.returncode == 0 and passed_count == discovered
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True, "passed": bool(passed),
            "command": "ctest -V --output-on-failure -R test_bpp_raa",
            "discovered": discovered, "passedCount": passed_count,
        }, ensure_ascii=False))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True, "passed": bool(passed),
            "command": "ctest -V --output-on-failure -R test_bpp_raa",
            "discovered": discovered, "passedCount": passed_count,
        }, ensure_ascii=False))
        self.run(f'{bash} -c "{ctest_bin} --output-on-failure -R test_bpp_raa"'
                 if os.path.isfile(bash)
                 else f"{ctest_bin} --output-on-failure -R test_bpp_raa",
                 cwd=self.build_folder, env="conanrun")
        if not passed:
            raise RuntimeError(
                f"test_package failed: exit={proc.returncode} passedCount={passed_count}/{discovered}")
