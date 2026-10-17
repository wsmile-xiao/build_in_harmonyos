#!/usr/bin/env python3
"""Conan test_package for jenkins-debian-glue 0.23.6.

Replays the upstream `make check` test suite (tests/increase-version-number,
tests/merge-conflict, tests/file-detection — originally shunit2-based, not
available on OHOS) against the packaged jdg-* scripts. The shunit2 assertions
are replayed 1:1 by test.sh using plain bash comparisons; fixtures are taken
from the upstream source tree.

Runtime tools used: bash, grep, file, ruby — all present on the OHOS PC
platform (/data/service/hnp/bin). No compilation involved.
"""
import os
import tempfile

from conan import ConanFile
from conan.errors import ConanException


class JenkinsDebianGlueTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["jenkins-debian-glue"]
        bindir = os.path.join(dep.package_folder, "bin")
        for prog in ("jdg-increase-version-number", "jdg-tap-merge-conflict",
                     "jdg-tap-shellcheck", "jdg-tap-perlcritic",
                     "jdg-tap-pep8"):
            if not os.path.isfile(os.path.join(bindir, prog)):
                raise ConanException(f"packaged program missing: {prog}")
        self.output.info(f"  jdg bin dir: {bindir}")

        test_dir = os.path.dirname(os.path.abspath(__file__))
        test_sh = os.path.join(test_dir, "test.sh")
        fixtures = os.path.join(test_dir, "fixtures")
        if not os.path.isfile(test_sh):
            raise ConanException("test.sh missing from test_package")

        # test() 无 layout 时 build_folder 即 source_folder；将日志写到
        # 系统临时目录避免污染归档（目录必须确保存在，CI worker 可能没有 ~/tmp）
        log_dir = tempfile.gettempdir()
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "jdg-test-package.log")
        cmd = (f'bash "{test_sh}" "{bindir}" "{fixtures}" > "{log_file}" 2>&1')
        rc = self.run(cmd, env="conanrun", ignore_errors=True)
        with open(log_file, "r", errors="replace") as fh:
            output = fh.read()
        self.output.info(output)
        if rc != 0 or "FAILED" in output:
            raise ConanException(f"upstream test replay failed (exit {rc})")
        self.output.info("upstream `make check` replay: ALL PASSED")
