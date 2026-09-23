#!/usr/bin/env python3
"""Conan test_package for distorm 3.5.2.b — Conan L1 official test.

Uses CMake to build the consumer tests (CMakeLists.txt already exists).
CMakeToolchain handles compiler settings automatically (R33 compliant).
CI runs this automatically via `conan create` (which invokes test_package).

Machine evidence (hmbs gate):
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount = 2 real ctest cases
  (test_version + test_decode, each a real library-API consumer binary).
  Markers are emitted only after both binaries exit 0; any failure emits
  passed=false before raising, so a pass can never be faked.
- HMBS_UPSTREAM_TEST_RESULT: status=no_tests. The upstream C library has
  no test suite (audit in test_package/MANIFEST.yml): no tests/ dir, no
  check/test target in make/linux/Makefile, examples are demos without
  assertions; the only real suite (python/test_distorm3.py, ~367 cases)
  targets the CPython binding and needs yasm + extension build, not the
  C library packaged here.
"""

import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class DistormTestConan(ConanFile):
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

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        discovered = 2
        passed = 0
        try:
            self.run(f"{bash} -c './test_version'", env="conanrun")
            passed += 1
            self.run(f"{bash} -c './test_decode'", env="conanrun")
            passed += 1
        except Exception as exc:
            self.output.error(f"test_package binary failed: {exc}")
        ok = (passed == discovered)
        tp_result = {
            "executed": True,
            "passed": ok,
            "command": "./test_version && ./test_decode",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_result, ensure_ascii=False))
        upstream_result = {
            "status": "no_tests",
            "framework": "none",
            "command": "N/A (upstream C library has no test suite)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "distorm 3.5.2b 上游 C 库侧无任何测试套件：顶层无 tests/、test/、check* 目录，"
                "无 CTest/CMake/meson 测试接线；make/linux/Makefile 仅 all/clean/clib/install 四个目标，"
                "无 check/test 目标；examples/tests/main.cpp 为固定 3 字节 decompose 演示（无断言，恒返回 0），"
                "其余 examples 均为平台演示或语言绑定示例；唯一实质套件 python/test_distorm3.py（约 367 个用例）"
                "测试对象是 CPython 绑定模块 distorm3 且约半数用例需 yasm 在线汇编，本配方仅打包 C 静态/动态库，"
                "OHOS 无 yasm 预编译包，无法低成本补齐。详见 test_package/MANIFEST.yml upstream_test_audit。"
            ),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_result, ensure_ascii=False))
        if not ok:
            raise Exception(f"test_package failed: passed {passed}/{discovered}")
