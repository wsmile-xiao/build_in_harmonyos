#!/usr/bin/env python3
"""test_package for opalmod — 真实执行验证（R34）。

不满足于"文件存在"，而是**逐个模块真实调用上游导出函数**：

  ① 5 个子模块（OpaL::where / read / dir / manipulate / action）均可被加载；
  ② **真实功能调用**：
     · OpaL::where::which("perl")            → 能定位可执行文件
     · OpaL::read::readscalarfile(<临时文件>) → 返回真实内容
     · OpaL::dir::getdirlist(<临时目录>)      → 返回目录项
     · OpaL::action 的 setDebugLevel/getDebugLevel → 取值往返一致
  ③ **负向**：加载一个不存在的模块必须失败（证明断言非恒真）。

⚠️ 必须 `env="conanrun"` 应用依赖 runenv：本包的 PERL5LIB 由 `package_info()`
注入（指向 .pm 实际所在目录），不应用则 Perl 找不到 OpaL::*。
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.layout import basic_layout

PERL_PARTS = ["where", "read", "dir", "manipulate", "action"]


class OpalmodTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if not can_run(self):
            self.output.info("opalmod: 交叉编译场景，跳过运行期测试")
            return

        pkg = self.dependencies[self.tested_reference_str].package_folder
        if not pkg:
            raise ConanException(f"无法解析被测包 {self.tested_reference_str} 的 package_folder")

        script = os.path.join(self.source_folder, "run_opalmod_tests.py")
        outdir = os.path.join(self.build_folder, "_opalmod_test")
        os.makedirs(outdir, exist_ok=True)
        log = os.path.join(self.build_folder, "opalmod_tests.log")

        # env="conanrun" —— 应用依赖 runenv，使 PERL5LIB 指向本包 .pm 所在目录
        self.run(f'python3 "{script}" "{pkg}" "{outdir}" > "{log}" 2>&1',
                 env="conanrun")
        with open(log, encoding="utf-8", errors="replace") as fh:
            result = fh.read()
        self.output.info(result.strip())

        m = re.search(r"RESULT: passed=(\d+) failed=(\d+) skipped=(\d+)", result)
        if not m:
            raise ConanException("opalmod: 未取得测试汇总行 RESULT:")
        passed, failed = int(m.group(1)), int(m.group(2))
        if failed or not passed:
            raise ConanException(
                f"opalmod: 消费者功能测试未通过（passed={passed} failed={failed}）")
        self.output.info(f"opalmod OK（{passed} 项校验通过）")
