#!/usr/bin/env python3
"""Conan test_package for minisign 0.12 — exercises the packaged CLI binary.

Upstream minisign 0.12 has NO test suite (audited: no tests/ dir, no
gtest/ctest, no enable_testing in CMakeLists.txt), so this test_package
runs real functional tests against the installed `minisign` binary:
version output, key generation, signing, verification and tamper detection.
The HMBS_UPSTREAM_TEST_RESULT marker reports the audited no-tests status;
the HMBS_TEST_PACKAGE_RESULT marker carries the real assertion counts.
"""
import json
import os

from conan import ConanFile


class MinisignTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Upstream test audit marker (hmbs machine-evidence gate):
        # minisign 0.12 has no automated tests of any kind.
        upstream = {
            "status": "no_tests",
            "framework": "none",
            "command": "audit: no upstream tests in minisign 0.12",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": ("minisign 0.12 源码树无 tests/、test/ 目录，无任何测试框架文件；"
                       "CMakeLists.txt 无 enable_testing()/add_test()/ctest 调用，无 test 目标；"
                       "GitHub release 0.12 资产仅含源码包与各平台预编译二进制，无独立测试套件。"
                       "详见 test_package/MANIFEST.yml upstream_test_audit。"),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))

        # Real functional tests of the packaged binary. test.sh prints the
        # HMBS_TEST_PACKAGE_RESULT marker itself with real counts (5 checks).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'"{bash}" test.sh', env="conanrun")
