#!/usr/bin/env python3
"""Conan test_package — unittestpp 2.0.0 消费者测试（L1）。

消费者视角验证（真实编译链接打包产物 libUnitTest++.a + 公共头文件）：

1. test_unittestpp — 正向：9 个 TEST/TEST_FIXTURE/SUITE 用例，用公共宏 API
   （CHECK/CHECK_EQUAL/CHECK_CLOSE/CHECK_ARRAY_*/CHECK_THROW/REQUIRE）覆盖
   框架核心行为，外加 Posix 平台层 Timer/SleepMs 与时间约束；RunAllTests()
   必须输出 "Success: 9 tests passed." 且退出码 0。
2. test_unittestpp_negative — 反向对照（预期失败）：3 个用例中 1 个通过、
   1 个 CHECK 失败、1 个 raise(SIGSEGV) 触发信号 —— 证明断言失败与崩溃信号
   都被框架如实捕获上报（Posix SignalTranslator 的 sigsetjmp/sigaction/siglongjmp
   在 OHOS 生效），预期退出码 = 失败数 2、输出含 FAILURE 摘要。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import load


class UnitTestppTestConan(ConanFile):
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

    def _binary(self, name):
        for root, _dirs, files in os.walk(self.build_folder):
            if name in files:
                return os.path.join(root, name)
        raise ConanException("测试可执行文件未找到: %s" % name)

    def test(self):
        positive = self._binary("test_unittestpp")
        log = os.path.join(self.build_folder, "positive-run.log")
        rc = self.run('"%s" > "%s" 2>&1' % (positive, log), ignore_errors=True)
        output = load(self, log)
        if rc != 0 or "Success: 9 tests passed." not in output:
            raise ConanException(
                "正向用例未按预期全过（rc=%s）：\n%s" % (rc, output[-2000:]))

        negative = self._binary("test_unittestpp_negative")
        neg_log = os.path.join(self.build_folder, "negative-run.log")
        neg_rc = self.run(
            '"%s" > "%s" 2>&1' % (negative, neg_log), ignore_errors=True)
        neg_output = load(self, neg_log)
        if neg_rc == 0:
            raise ConanException(
                "反向对照未按预期失败——框架吞掉了失败用例：\n%s" % neg_output[-2000:])
        for marker in ("check_failure_probe", "signal_probe",
                       "Unhandled exception: test crashed",
                       "FAILURE: 2 out of 3 tests failed (2 failures)."):
            if marker not in neg_output:
                raise ConanException(
                    "反向对照输出缺少预期标记 %r：\n%s"
                    % (marker, neg_output[-2000:]))
        self.output.info(
            "negative control rc=%s: failures and crash signals reported as expected"
            % neg_rc)
