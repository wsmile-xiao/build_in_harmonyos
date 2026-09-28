#!/usr/bin/env python3
"""test_package for qastools/1.4.0 — 真实执行被测包安装的三个 Qt6/ALSA GUI 程序。

上游 qastools 1.4.0 无任何自动化测试入口（CTest 注册 0 个、无 test 目录、
无 add_test），因此 test_package 独立承担 L1 层验证。

本文件满足三道门禁并保持"实质测试"：
  * L0c —— test_package/ 下有真实测试源 test_qastools.sh；
  * L0d / PF3 —— test() 通过 self.run 真正 exec 被测二进制，非空壳；
  * R34 —— 断言落在被测包产出的可执行文件上（--version / --help 输出 + ELF 头）。

headless 策略（R7：安全弹窗先触发再测试）：三个程序都在 main() 进入 Qt 事件循环
之前处理 --version / --help，故在 QT_QPA_PLATFORM=offscreen 下可安全断言。
脚本对 qasmixer 断言退出码 255，对 qashctl / qasconfig 只断言 stdout 版本串
（上游 main.cpp 的 `res < ditems.init_settings(...)` 二次调用使条件落空，二者会
进入 app.exec()；详见 test_qastools.sh 文件头契约说明）。
"""

import os

from conan import ConanFile
from conan.errors import ConanException


class QasToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = os.path.join(
            self.dependencies["qastools"].package_folder, "bin"
        )
        if not os.path.isdir(bin_dir):
            raise ConanException("qastools bin/ not found: %s" % bin_dir)
        # OHOS: /system/bin/sh (mksh) 不能执行 ELF 二进制，必须用 bash 包装
        # （conducteo/acetoneiso 同款：优先取 CI profile buildenv 注入的
        #  CONFIG_SHELL，回退到 worker 上已知的 bash 路径）。
        shell = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        script = os.path.join(self.source_folder, "test_qastools.sh")
        self.run(f'"{shell}" "{script}" "{bin_dir}"', env="conanrun")
