#!/usr/bin/env python3
"""test_package for lie 2.2.2 — 消费者侧真实执行已安装的 lie 包装脚本。

executable 包无可链接库，走 VirtualRunEnv 直跑二进制（L1a/L1b 口径）：
test.sh 通过 conanrun PATH 拿到本包 bin/lie，断言 ①算术核心 ②`?help`/`?dim`
帮助数据（走 printexpr → 验证 0001 NULL 补丁在 /tmp EROFS 下不再 SIGSEGV）
③干净退出码。上游断言计数见 MANIFEST.yml，消费者断言独立分栏。
"""

from conan import ConanFile


class LieTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 真实消费者执行：lie 包装脚本 → Lie.exe（不是 echo/print 空壳，L1d 口径）
        self.run("sh test.sh", env="conanrun")
