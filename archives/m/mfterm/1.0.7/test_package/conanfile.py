#!/usr/bin/env python3
"""Conan test_package — mfterm 1.0.7（application 型）.

被测包是命令行工具（无库导出），测试分两部分：
  1. 通用消费者冒烟测试（run_mfterm_test.sh）：真实执行被测包二进制
     （R34/PF3 口径）—— --version/--help 参数解析 + 无硬件离线命令
     `mac key`/`mac compute 0`（Crypto-1 MAC 算法核心，纯离线计算，
     2026-09-20 试编译目录真机实测通过）。
  2. 鸿蒙平台特有测试（harmonyos_specific_test.c）：编译期硬绑定
     OHOS/AArch64 工具链 + 运行时校验 mfterm ELF64/AArch64/动态链接器/
     NEEDED 依赖等平台属性。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.gnu import AutotoolsDeps
from conan.tools.layout import basic_layout


class MftermTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 鸿蒙特有测试校验 mfterm 的 NEEDED 运行库（libnfc），须直链
        self.requires("libnfc/1.8.0")

    def layout(self):
        basic_layout(self)

    def generate(self):
        # 生成 conanautotoolsdeps.sh（含 libnfc + libusb-compat + libusb 的
        # CPPFLAGS/LDFLAGS/LIBS 传递 flags），供 build() 编译 C 测试程序时注入
        AutotoolsDeps(self).generate()

    def build(self):
        # 鸿蒙特有测试：用 OHOS clang 编译，链接 libnfc 静态库（含传递依赖）
        src = os.path.join(self.source_folder, "harmonyos_specific_test.c")
        out = os.path.join(self.build_folder, "harmonyos_specific_test")
        cc = os.environ.get("CC", "clang")
        # 依赖 flags 由 conanbuild 环境注入（CPPFLAGS 含 -I<nfc>/include，
        # LDFLAGS/LIBS 含 -lnfc -lusb -lusb-1.0 -ldl -lpthread）
        self.run(
            '%s "%s" -o "%s" $CPPFLAGS $CFLAGS $LDFLAGS $LIBS' % (cc, src, out),
            env="conanbuild",
        )

    def test(self):
        if cross_building(self):
            return

        # 1. 鸿蒙平台特有测试（编译期已绑 OHOS/AArch64）
        test_bin = os.path.join(self.build_folder, "harmonyos_specific_test")
        self.run('"%s" "%s"' % (test_bin, self._mfterm_bin()), env="conanrun")

        # 2. 通用消费者冒烟测试：真实执行被测包二进制
        script = os.path.join(self.source_folder, "run_mfterm_test.sh")
        # HMDFS 上 chmod +x 不生效（E011），经 sh 解释器调用，不依赖执行位
        self.run('sh "%s" "%s"' % (script, self._mfterm_bin()), env="conanrun")

    def _mfterm_bin(self):
        pkg = self.dependencies["mfterm"]
        return os.path.join(pkg.package_folder, "bin", "mfterm")
