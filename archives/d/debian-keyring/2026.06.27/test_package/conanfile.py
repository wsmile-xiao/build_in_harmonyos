#!/usr/bin/env python3
"""debian-keyring 2026.06.27 test_package —— 纯数据包，无需编译。

跑两件事（对应 PR 正文的测试三栏）：
1. `consumer_keyring.py` —— 消费者用例：把 share/keyrings 当可信密钥库消费
   （按 sha512sums.txt 核完整性 → 解析 OpenPGP 数据流建索引 → 按 keyid/指纹做
   apt Signed-By 式查找 → 未受信 keyid 必须查不到）。
2. `test_keyring.py` —— 适配自检：交付物齐备、包结构自洽、
   "公钥包（tag 6）个数 == jetring 源目录里的 0x* 文件数"。
"""

import os
import sys

from conan import ConanFile


class DebianKeyringTestConan(ConanFile):
    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["debian-keyring"]
        package_folder = dep.package_folder
        data_dir = os.path.join(package_folder, "share", "keyrings")
        consumer = os.path.join(self.source_folder, "consumer_keyring.py")
        script = os.path.join(self.source_folder, "test_keyring.py")
        # 消费者用例：真的把密钥环当可信库用起来
        self.run(f"{sys.executable} {consumer} {package_folder}")
        # 适配自检
        self.run(f"{sys.executable} {script} {data_dir} {package_folder}")
