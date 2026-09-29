#!/usr/bin/env python3
"""debian-design 3.0.29 test_package —— 纯数据包，无需编译。

完整消费者用例（平台 rule12）：`consumer_design.py` 按 live-build / debian-installer 的
方式消费本包 —— 把 `nodes/*.yml`（节点类清单）+ `skel/*.in` 模板组合成
`content/<node>/{preseed.cfg,script.sh}`（等价上游 `boxer compose ... <node>`），
再像 `Makefile` 的 `all` 目标那样生成 `MD5SUMS`/`SHA256SUMS`，最后**以消费方口径验收**：
校验和逐条回算一致、preseed 每行是合法 debconf 指令（含续行）、`script.sh` 通过 `sh -n`。

上游 N=0：源包内无 `test/`/`tests/`、无 `check`/`test` 目标、无 `debian/tests/`；
上游 `Makefile` 的组合依赖外部的 `boxer`（不在本包内），故组合与验收由消费者用例接管。
"""
import os
import sys

from conan import ConanFile


class DesignBlendTestConan(ConanFile):
    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["debian-design"].package_folder

        # ① 完整消费者用例（平台 rule12）：组合 + 以消费方口径验收
        consumer = os.path.join(self.source_folder, "consumer_design.py")
        self.run(f"{sys.executable} {consumer} {package_folder}")

        # ② 适配自检（M=7，非上游用例；上游 N=0）
        script = os.path.join(self.source_folder, "test_design.py")
        self.run(f"{sys.executable} {script} {package_folder}")
