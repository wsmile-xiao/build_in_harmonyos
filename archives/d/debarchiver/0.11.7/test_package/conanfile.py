#!/usr/bin/env python3
"""test_package for debarchiver — 真实执行验证（R34）。

本包是 `#!/usr/bin/env perl` 的脚本，且依赖 opalmod（`use OpaL::*`）。
故 test 必须：
  1. `generate()` 生成依赖 runenv；
  2. `test()` 中 `self.run(..., env="conanrun")` **显式应用** —— 只生成不应用无效，
     否则 `env perl` 可能解析到设备自身的 perl，与依赖 perl 的 XS 模块 ABI 不符
     （实测过同类问题：loadable library and perl binaries are mismatched）。

★ 关键：`--configfile` 绕过硬编码目录
   上游把 `$inputdir`/`$destdir`/`$cachedir` 硬编码为 `/var/lib/debarchiver` 与
   `/var/cache/debarchiver`；这些目录不存在时脚本 `chdir` 失败并以 `EXIT: 2` 退出。
   **实测 `--configfile <file>` 可覆盖它们** → 测试内生成临时配置指向 build 目录，
   使脚本能在非 root、无 /var/lib 的环境下真实运行。

⚠️ 版本断言按实测值：`--version` 输出 `Debian package archiver, version 0.10`
   —— 上游脚本内的版本串是 **0.10**，与 Debian 包版本 0.11.7 **不同**（上游未同步
   更新该字符串）。断言写 0.11.7 会假失败，故按实际输出断言并记录该差异。
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.layout import basic_layout


class DebarchiverTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)
        # ★ 必须**直接**声明 opalmod，不能只依赖 debarchiver 的传递依赖：
        #   debarchiver 的 package_type="application" 会让其依赖 opalmod 在消费者
        #   图中被判为 "Skipped binaries"（实测 `conan install` 日志），于是 opalmod
        #   的 runenv_info（PERL5LIB）**不会传播**过来 →
        #       Can't locate OpaL/action.pm in @INC
        #   实测对照：仅经 debarchiver 传递时 runenv 中 opalmod 路径数 = 0；
        #             直接声明后 = 8，问题消失。
        #   被测程序 `debarchiver` 运行期确实需要 OpaL::*，故此处直接声明是正确语义。
        self.requires("opalmod/0.2.2.1")

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if not can_run(self):
            self.output.info("debarchiver: 交叉编译场景，跳过运行期测试")
            return

        pkg = self.dependencies[self.tested_reference_str].package_folder
        if not pkg:
            raise ConanException(f"无法解析被测包 {self.tested_reference_str} 的 package_folder")

        script = os.path.join(self.source_folder, "run_debarchiver_tests.py")
        outdir = os.path.join(self.build_folder, "_debarchiver_test")
        os.makedirs(outdir, exist_ok=True)
        log = os.path.join(self.build_folder, "debarchiver_tests.log")

        self.run(f'python3 "{script}" "{pkg}" "{outdir}" > "{log}" 2>&1',
                 env="conanrun")
        with open(log, encoding="utf-8", errors="replace") as fh:
            result = fh.read()
        self.output.info(result.strip())

        m = re.search(r"RESULT: passed=(\d+) failed=(\d+) skipped=(\d+)", result)
        if not m:
            raise ConanException("debarchiver: 未取得测试汇总行 RESULT:")
        passed, failed = int(m.group(1)), int(m.group(2))
        if failed or not passed:
            raise ConanException(
                f"debarchiver: 消费者功能测试未通过（passed={passed} failed={failed}）")
        self.output.info(f"debarchiver OK（{passed} 项校验通过）")
