#!/usr/bin/env python3
"""test_package for deb2targz — 真实执行验证（R34）。

⚠️ 两处必须同时做对，否则测试会在错误的 perl 上运行：

1. `generate()` 生成依赖的 runenv（VirtualRunEnv）；
2. `test()` 中 `self.run(..., env="conanrun")` **显式应用**该 runenv
   —— 只生成不应用无效：本包产品是 `#!/usr/bin/env perl` 脚本，`env` 按 **PATH**
   解析 perl，若 runenv 未生效，会解析到设备自身的 perl（实测本机
   `/data/service/hnp/bin/perl` 为 5.42.0），而它去加载 conan perl（5.42.2）的
   XS 模块 `IO.so` → 报
       IO.c: loadable library and perl binaries are mismatched
       (got first handshake key 0xf880080, needed 0xf180080)
   （实测：`env="conanrun"` 后 PATH 首位变为依赖 perl 的 bin，问题消失。）

另注：Conan 2 的 `self.run()` 不回传输出，故把测试日志重定向到文件后再读并
据 `RESULT:` 汇总行判定成败（与仓库内 triehash 配方同一做法）。
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.layout import basic_layout


class Deb2TargzTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # 生成依赖（perl）的运行环境脚本；须配合 test() 中的 env="conanrun" 使用
        VirtualRunEnv(self).generate()

    def test(self):
        if not can_run(self):
            self.output.info("deb2targz: 交叉编译场景，跳过运行期测试")
            return

        # ⚠️ test_package 的 self.package_folder 指向 test_package 自己，
        # 取被测包目录须走 self.dependencies
        pkg = self.dependencies[self.tested_reference_str].package_folder
        if not pkg:
            raise ConanException(f"无法解析被测包 {self.tested_reference_str} 的 package_folder")

        script = os.path.join(self.source_folder, "run_deb2targz_tests.py")
        outdir = os.path.join(self.build_folder, "_deb2targz_test")
        os.makedirs(outdir, exist_ok=True)
        log = os.path.join(self.build_folder, "deb2targz_tests.log")

        # env="conanrun" —— 关键：应用依赖 runenv，使 `env perl` 解析到 conan perl
        self.run(f'python3 "{script}" "{pkg}" "{outdir}" > "{log}" 2>&1',
                 env="conanrun")
        with open(log, encoding="utf-8", errors="replace") as fh:
            result = fh.read()
        self.output.info(result.strip())

        m = re.search(r"RESULT: passed=(\d+) failed=(\d+) skipped=(\d+)", result)
        if not m:
            raise ConanException("deb2targz: 未取得测试汇总行 RESULT:")
        passed, failed = int(m.group(1)), int(m.group(2))
        if failed or not passed:
            raise ConanException(
                f"deb2targz: 消费者功能测试未通过（passed={passed} failed={failed}）")
        self.output.info(f"deb2targz OK（{passed} 项校验通过）")
