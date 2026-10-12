#!/usr/bin/env python3
"""Conan test_package — ptunnel 0.72 consumer functional test.

ptunnel has no upstream test suite (see MANIFEST.yml), so this test exercises
the packaged binary end-to-end via test_ptunnel.sh:
- bin/ptunnel exists and is executable
- running it with `-h` prints the 'Usage:' + 'ptunnel v' banner and exits
  non-zero (deterministic; full tunneling needs root + a capture device +
  live ICMP, unavailable in a build-test sandbox)
"""
import json
import os
import shutil

from conan import ConanFile


class PtunnelTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R5/OHOS: use CONFIG_SHELL bash (no /bin/sh for script execution)
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        script = os.path.join(self.source_folder, "test_ptunnel.sh")
        self.run(f'{bash} {script} "{bin_dir}"', env="conanrun")

        # HMBS 机器证据标记：上游 no_tests（见 test_package/MANIFEST.yml 的
        # upstream_test_audit 审计结论——上游发布包无 check/test/TESTS 目标、
        # 无 tests/ 目录、无任何测试框架/CI 配置，upstream_test_total: 0）。
        # 在真实运行 test_ptunnel.sh（已输出 HMBS_TEST_PACKAGE_RESULT）之后
        # 再复发行，status=no_tests、各计数为 0。
        upstream_marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": ("upstream ptunnel 0.72 无任何测试；审计见 "
                       "test_package/MANIFEST.yml 的 upstream_test_audit：Makefile 仅定义 "
                       "all/dist/ptunnel/ptunnel.exe/clean/depend/install 目标，"
                       "无 check/test/TESTS/check_PROGRAMS/check-local，make -n check 报 "
                       "'No rule to make target'；源码仅 ptunnel.c + RFC 参考 md5.c，无自测框架；"
                       "归档无 tests/ 目录。upstream_test_total: 0"),
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker))
