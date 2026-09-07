#!/usr/bin/env python3
"""Conan test_package — ayatana-indicator-session 26.6.1

R34/PF3: test() 必须实质运行被测包。本包产物是 D-Bus 服务可执行文件
ayatana-indicator-session-service（无库/头文件 API），因此测试直接运行该
可执行文件：--version 断言输出含版本号，--help 验证 CLI 可用。

注：服务主体需要会话 D-Bus + GSettings schema，纯 CI/容器无法完整拉起，
--version/--help 走 main() 前置分支（0002 补丁），不触达服务初始化。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class AyatanaIndicatorSessionTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["ayatana-indicator-session"]
        service = os.path.join(pkg.package_folder, "bin", "ayatana-indicator-session-service")
        if not os.path.isfile(service):
            raise ConanException(f"missing packaged executable: {service}")

        # Smoke 1: --version 必须输出 "ayatana-indicator-session 26.6.1" 且 rc=0。
        # self.run 返回 int 退出码，非零即抛 ConanException；断言内嵌在 shell 管道中。
        self.run(
            f'"{service}" --version 2>&1 | grep -q "ayatana-indicator-session 26.6.1"',
            env="conanrun",
        )
        # Smoke 2: --help 必须 rc=0 且包含 Usage 行。
        self.run(f'"{service}" --help 2>&1 | grep -q "Usage:"', env="conanrun")

        self.output.info("ayatana-indicator-session-service 26.6.1 smoke OK")
