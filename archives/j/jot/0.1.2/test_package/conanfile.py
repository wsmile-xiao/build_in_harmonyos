#!/usr/bin/env python3
"""Conan test_package — jot 0.1.2.

验证 jt 可执行并实际运行（R34：实质执行被测包二进制）。

执行 test_jt.sh（2 条真实断言：可执行性 + jt --help 实际运行产出非空输出），
运行结束后输出 HMBS_TEST_PACKAGE_RESULT 标记（discovered=2, passedCount=2）。

上游测试：jot 0.1.2 经源码审计无任何测试（见 MANIFEST.yml upstream_test_audit），
每轮重发 HMBS_UPSTREAM_TEST_RESULT status:"no_tests"（缓存命中导致 build() 被跳过
时，test_package 阶段仍提供 no_tests 证据，cargo-seek/0.1.0 先例）。
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class JotTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-build: runtime test deferred to OHOS/shadow CI")
            return
        bin_dir = os.path.join(self.dependencies["jot"].package_folder, "bin")
        script = os.path.join(self.source_folder, "test_jt.sh")
        self.run(f'sh "{script}" "{bin_dir}"')

        # HMBS evidence: test_package executed 2 real assertions
        # (1. jt executable; 2. jt --help runs and produces non-empty output)
        actual_cmd = f'sh "{script}" "{bin_dir}"'
        tp_marker = {
            "executed": True,
            "passed": True,
            "command": actual_cmd,
            "discovered": 2,
            "passedCount": 2,
        }
        tp_msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker, ensure_ascii=False)
        print(tp_msg, flush=True)
        self.output.info(tp_msg)

        # HMBS upstream evidence: re-emit no_tests every round
        # (build() may be skipped on cache hit)
        upstream = {
            "status": "no_tests",
            "framework": "cargo-test",
            "command": "",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "Audited shashwatah/jot v0.1.2 source (sha256 "
                      "d7da3220c29102ee7c51e2a5656ceb6672ae3b85be22c5ddcd176b330c6029c9): "
                      "no tests/ dir; no #[test]/#[cfg(test)] in any of the 11 src/ files; "
                      "Cargo.toml has no [dev-dependencies]; no .github CI workflow. "
                      "Therefore status no_tests."
        }
        up_msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        print(up_msg, flush=True)
        self.output.info(up_msg)
