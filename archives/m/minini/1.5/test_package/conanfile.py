#!/usr/bin/env python3
"""minini 1.5 test_package —— 真实 C 消费者 + 交付形态自检。

① **完整消费者用例（平台 rule12）**：`test_minini.c` 把 minIni 当成真实配置层用一遍
   （写入 6 个键 → 读回字符串/整数/布尔/浮点 → 默认值语义 → 存在性判定 →
   段/键枚举与 ini_browse 全量遍历 → 覆盖写 + 删键 → 用上游夹具验证尾随注释与
   无段落 INI 解析），16 项可核对结果。
② **适配自检（M）**：`test_layout.py` 检查交付形态（静态库/头/内嵌源码/许可/纯净性）。

上游自带的测试程序（`dev/test.c`，29 条断言）在 recipe 的 build() 里跑。
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.tools.build import cross_building


class MininiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["minini"]
        inc = " ".join("-I" + p for p in dep.cpp_info.includedirs)
        libdirs = " ".join("-L" + p for p in dep.cpp_info.libdirs)
        conf = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = conf.get("c", "cc")
        self.run(
            '%s -O2 %s test_minini.c -o test_minini %s -lminIni -lm'
            % (cc, inc, libdirs))

    def test(self):
        workdir = os.path.join(self.build_folder, "consumer-work")
        os.makedirs(workdir, exist_ok=True)
        # 消费者用例需要上游夹具（test.ini / testplain.ini）
        for name in ("test.ini", "testplain.ini"):
            shutil.copy(os.path.join(self.source_folder, name), workdir)
        if cross_building(self):
            self.output.info("cross-building：只验编译 + 链接（原生构建时才会执行）")
        else:
            self.run("%s %s" % (os.path.join(self.build_folder, "test_minini"), workdir),
                     env="conanrun")
        layout = os.path.join(self.source_folder, "test_layout.py")
        self.run("%s %s %s" % (sys.executable, layout,
                               self.dependencies["minini"].package_folder))
