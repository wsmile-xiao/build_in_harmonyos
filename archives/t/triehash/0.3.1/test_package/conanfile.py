#!/usr/bin/env python3
"""Conan test_package for triehash 0.3.1（纯 Perl 脚本）。

真实执行被测脚本（R34）：由 test_package/run_triehash_tests.sh 完成 6 项校验，
并解析其 `RESULT: passed=N failed=M` 汇总行；failed>0 或 passed==0 一律报错。

为何不直接用上游 tests/：其 tests/framework.sh 通过
`perl -MDevel::Cover=...` 运行被测脚本，而 Devel::Cover 不在 ohpcd 的 perl 包内
（实测 Can't locate Devel/Cover.pm），故改用本脚本做等价的功能验证。
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class TriehashTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: skipping runtime execution")
            return

        script = os.path.join(self.source_folder, "run_triehash_tests.sh")
        out_dir = os.path.join(self.build_folder, "_triehash_test")
        os.makedirs(out_dir, exist_ok=True)

        # Conan 2 的 self.run() 不返回输出 → 重定向到文件后再读
        log = os.path.join(self.build_folder, "triehash_tests.log")
        self.run(f'sh "{script}" "triehash" "{out_dir}" > "{log}" 2>&1',
                 env="conanrun")
        with open(log, encoding="utf-8", errors="replace") as fh:
            result = fh.read()
        self.output.info(result.strip())

        m = re.search(r"RESULT: passed=(\d+) failed=(\d+)", result)
        if not m:
            raise ConanException("triehash: 未取得测试汇总行")
        passed, failed = int(m.group(1)), int(m.group(2))
        if failed or not passed:
            raise ConanException(
                f"triehash: 消费者功能测试未通过（passed={passed} failed={failed}）")
        self.output.info(f"triehash OK（{passed} 项校验通过）")
