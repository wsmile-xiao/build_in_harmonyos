#!/usr/bin/env python3
"""Conan test_package — kamailio-extras 6.0.6 L1 消费者视角测试。

31 个模块 .so 由 kamailio 运行时 loadmodule（dlopen）加载：核心符号由 kamailio
主程序提供，脱离主程序无法独立 dlopen。故本测试按 **加载器同源语义** 对产物做
实质校验 —— kamailio 加载模块时读的是模块导出结构 `struct module_exports` 的
首字段 `char *name`（src/core/sr_module.h）并以此注册模块；本测试自解析 ELF
（PT_LOAD / .dynsym / .symtab / .rela.dyn / .dynamic）读取该字段并逐一比对。
"""
import os
import sys

from conan import ConanFile
from conan.tools.env import Environment


class KamailioExtrasTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34 实质验证：对打包产物 31 个模块 .so 做真实检查
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        mods_dir = os.path.join(package_folder, "lib", "kamailio", "modules")
        assert os.path.isdir(mods_dir), f"模块目录不存在: {mods_dir}"

        checker = os.path.join(self.source_folder, "check_extras_modules.py")
        env = Environment()
        env.define("KAMAILIO_EXTRAS_PACKAGE_FOLDER", package_folder)
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{checker}"')
