#!/usr/bin/env python3
"""Conan test_package — syslog-ng 4.8.1（守护进程 + dlopen 模块，tool 包）。

在原包之上做消费者级验证：conanrun 环境导出 PATH（bin/sbin）/
LD_LIBRARY_PATH（lib、lib/syslog-ng、依赖库）/ SYSLOGNG_PREFIX（模块目录
根），test.sh 依次验证版本横幅与模块目录重定位、模块注册表（全量 dlopen）、
配置解析与完整启动检查、以及端到端守护进程路由（internal() → file()）
+ syslog-ng-ctl stats + SIGTERM 优雅退出。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class SyslogNgTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # 绝对路径调脚本（test() 的 cwd 是测试包 build 目录，不保证
            # 含 test.sh）；build_folder 作为可写工作目录传入。
            test_script = os.path.join(self.source_folder, "test.sh")
            self.run(f'sh "{test_script}" "{self.build_folder}"', env="conanrun")
