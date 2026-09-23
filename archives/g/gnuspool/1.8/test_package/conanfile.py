#!/usr/bin/env python3
"""Conan test_package — gnuspool/1.8 消费者测试。

以使用者身份运行随包发布的 gspl-cjlist（打印队列作业列表工具），
断言逻辑放在 test.sh（可独立复跑），test() 负责在 conan 运行环境下调用它。
"""
import os

from conan import ConanFile


class GnuspoolTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = self.dependencies[self.tested_reference_str].cpp_info.bindirs[0]
        tool = os.path.join(bin_dir, "gspl-cjlist")
        script = os.path.join(self.recipe_folder, "test.sh")
        self.output.info("running consumer test: sh %s %s" % (script, tool))
        self.run('sh "%s" "%s"' % (script, tool), env="conanrun")
        self.output.info("gnuspool 消费者测试通过（gspl-cjlist 用法输出 + 随包 help 数据）")
