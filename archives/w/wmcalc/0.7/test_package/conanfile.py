#!/usr/bin/env python3
"""Conan test_package — wmcalc 0.7.

wmcalc 是 X11 dockapp（application 包，无库可链接），R34 要求测试**真实执行
被测二进制**。选两条无需 X server 即可判定的路径：

  * `wmcalc -h`：arg parsing 里的 `-h` 分支在 XOpenDisplay **之前**
    调用 show_usage()，打印 ` <app_name> <PACKAGE_VERSION>` 与 usage 面板后
    exit(OKAY=0)（wmcalc.c:138 / 836-851 一手取证）。PACKAGE_VERSION 由
    configure 的 DEFS 注入（configure:582 `PACKAGE_VERSION='0.7'`、
    4099 `DEFS=\`sed -n "$ac_script" confdefs.h\``）⇒ 版本串走的是真实编译期
    宏，不是脚本回显。
  * `wmcalc -d :99`：XOpenDisplay 失败分支 error_handler(ERR_X_DISPLAY)
    打印 "Could not open display on :99" 后 exit(err_code)（wmcalc.c:153 /
    895-905）⇒ 鸿蒙 PC 无真实 X display，这条就是本包交付口径里的
    "真实失败形态"（bridge-utils/1.5、memdump/1.01 同款申报）。

脚本按 xeyes/xidle 已过门禁的口径执行：用注入的 SHELL/CONFIG_SHELL
（设备实测 /bin/bash 与 /usr/bin/python3 均 MISSING，只有 /bin/sh=toybox ash）
跑 POSIX sh 脚本，不用 `set -eu`、不用 pipefail。
"""
import os

from conan import ConanFile


class WmcalcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["wmcalc"]
        binary = os.path.join(package.package_folder, "bin", "wmcalc")
        script = os.path.join(self.recipe_folder, "test_wmcalc.sh")
        shell = (os.environ.get("SHELL") or os.environ.get("CONFIG_SHELL")
                 or "/bin/sh")
        if not os.path.isfile(shell):
            shell = "/bin/sh"
        self.run(f'"{shell}" "{script}" "{binary}"', env="conanrun")
