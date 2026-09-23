#!/usr/bin/env python3
"""Conan test_package for libhwy_test 1.3.0.

消费者视角：用 CMakeDeps 暴露的 hwy::hwy_test + 包内安装的
hwy/tests/{test_util.h,test_util-inl.h,hwy_gtest.h} 编译并**真跑**
test_libhwy_test.cpp（15 项显式 Check：交付头文件版本指纹、hwy 核心库可用性、
RandomState 确定性、TypeName 命名、RandomFiniteValue、Set/Store 往返、
ForAllTypes/ForPartialVectors 枚举面、hwy_gtest 过滤器），并把真机实测到的
检查数打成 HMBS_TEST_PACKAGE_RESULT 标记（数字由用例自报行解析，不硬编码）。
"""
import glob
import json
import os
import re

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibhwyTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _find_exe(self):
        hits = [p for p in glob.glob(os.path.join(self.build_folder, "**", "test_libhwy_test"),
                                    recursive=True)
                if os.path.isfile(p) and os.access(p, os.X_OK)]
        if not hits:
            raise RuntimeError("consumer test binary not found under %s" % self.build_folder)
        hits.sort(key=len)
        return hits[0]

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: compile/link check completed")
            return
        exe = self._find_exe()
        log = os.path.join(self.build_folder, "consumer-run.log")
        # OHOS: /system/bin/sh 不能直接执行 ELF，用 profile 提供的 bash 包裹
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run('%s -c "%s > %s 2>&1"' % (bash, exe, log), env="conanrun",
                 cwd=self.build_folder)
        output = open(log, encoding="utf-8", errors="replace").read() if os.path.isfile(log) else ""
        self.output.info("HMBS_TEST_PACKAGE_LOG_TAIL=" + json.dumps(
            output.strip().splitlines()[-20:], ensure_ascii=False))
        m = re.search(r"checks_total=(\d+) checks_passed=(\d+) checks_failed=(\d+)", output)
        if not m:
            self.output.error(output[-2000:])
            raise RuntimeError("consumer test did not report its check counts")
        total, passed, failed = (int(x) for x in m.groups())
        test_pkg = {
            "executed": True,
            "passed": failed == 0 and passed == total and total > 0,
            "command": os.path.basename(exe),
            "discovered": total,
            "passedCount": passed,
            "failedCount": failed,
        }
        if not test_pkg["passed"]:
            self.output.error(output[-2000:])
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg))
            raise RuntimeError("libhwy_test consumer checks failed")
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg))
