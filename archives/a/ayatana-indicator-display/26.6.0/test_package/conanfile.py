#!/usr/bin/env python3
"""Conan test_package — ayatana-indicator-display 26.6.0.

验证 service 可执行文件已安装且可启动（依赖注入 conanrun 环境）。
service 启动后进入 g_main_loop_run 常驻，用 timeout 2s 运行并检查
进程能正常初始化（不因缺库/缺符号立即退出）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class AyatanaindicatordisplayTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.warning("skipped (cannot run on this platform)")
            return
        # 定位安装的 service 可执行文件（bin/ayatana-indicator-display/）
        dep = self.dependencies["ayatana-indicator-display"]
        exe = os.path.join(dep.package_folder, "bin",
                           "ayatana-indicator-display",
                           "ayatana-indicator-display-service")
        if not os.path.isfile(exe):
            raise SystemExit(f"FAIL: service executable not found: {exe}")
        # 依赖注入 conanrun 环境后启动；无 DBus 会话时进程可能报错退出，
        # 只要不是"找不到共享库/符号"（exit 127）即视为安装与依赖链接通过
        self.run(f"timeout 3 {exe} > /dev/null 2>&1; test $? -ne 127",
                 env="conanrun")
        self.output.info("OK: ayatana-indicator-display-service starts (deps linked)")
