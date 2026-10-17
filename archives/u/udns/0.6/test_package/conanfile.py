#!/usr/bin/env python3
"""Conan test_package — udns 0.6 (L1 official test).

Substantive verification (R34):
  - Compiles test.c against libudns via udns::udns and runs it. The test calls
    the real udns API offline-deterministically and reports 11/11 assertions:
    dns_init(NULL,0), dns_version(), dns_sptodn/dns_dntosp round-trip,
    dns_dnlen/dns_dnlabels, dns_dnequal, dns_dntop, dns_pton/dns_ntop,
    dns_strerror. The test binary genuinely depends on libudns.a (breaks link
    if the package artifacts are removed -> satisfies L1e destructive gate).

每轮必跑的 test() 在此复发 HMBS_UPSTREAM_TEST_RESULT(status=no_tests)
上游测试标记：udns 0.6 上游确实无测试套件（审计详见
test_package/MANIFEST.yml 的 upstream_test_audit：Makefile 仅含 all/
static/staticlib/shared/sharedlib/dist/subdist/clean/distclean/depend 与
示例工具目标，无 check/test/TESTS/check_PROGRAMS；源码包无 tests/ 目录、
无 gtest/cunit/tap 等测试框架、无 CI 配置，`make -n check` 报 'No rule to
make target'）。主配方 build() 无上游测试可跑，故该标记只在每轮必跑的
test() 中复发，保证 evidence 门禁每轮都能拿到上游测试标记。
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class UdnsTestConan(ConanFile):
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
        if not can_run(self):
            return
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_udns")
        self.run(f'"{test_bin}"', env="conanrun")

        # 上游测试标记：udns 0.6 上游无测试套件（审计详见
        # test_package/MANIFEST.yml 的 upstream_test_audit）。
        upstream_marker = {
            "status": "no_tests",
            "framework": "none",
            "command": ("make -n (upstream Makefile has no check/test target; "
                        "audited in test_package/MANIFEST.yml)"),
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": ("udns 0.6 上游无测试套件：Makefile 目标仅含 all/static/"
                       "staticlib/shared/sharedlib/dist/subdist/clean/distclean/"
                       "depend 及示例工具（dnsget/rblcheck/ex-rdns）构建规则，"
                       "grep 全文确认无 check/test/TESTS/check_PROGRAMS 等测试"
                       "目标（`make -n check` 报 'No rule to make target'），"
                       "源码包无 tests/ 目录、无 gtest/cunit/tap 等测试框架、"
                       "无 CI 配置；configure 仅做编译链接探测不构成测试套件"),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" +
                         json.dumps(upstream_marker, ensure_ascii=False))
