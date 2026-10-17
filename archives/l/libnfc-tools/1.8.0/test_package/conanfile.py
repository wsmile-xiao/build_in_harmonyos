#!/usr/bin/env python3
"""Conan test_package — libnfc-tools 1.8.0（application 型）.

被测包是命令行工具集（无库导出），测试分两部分：
  1. 通用消费者冒烟测试（run_nfc_tools_test.sh）：真实执行被测包二进制
     （R34/PF3 口径），无 NFC 硬件时 nfc-list 打印 "No NFC device found."
     并返回 0（2026-09-16 真机实测；该退出码仅作参考，脚本只把 126/127
     这类加载失败判为 FAIL），并校验 21 个工具齐全。
  2. 鸿蒙平台特有测试（harmonyos_specific_test.c）：编译期硬绑定 OHOS/AArch64
     工具链 + 运行时链接 libnfc 调用 nfc_version() 校验依赖库 ABI 在鸿蒙 musl 上可用。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.gnu import AutotoolsDeps
from conan.tools.layout import basic_layout


class LibnfctoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 鸿蒙特有测试需直接链接 libnfc（被测包不导出其依赖）
        self.requires("libnfc/1.8.0")

    def layout(self):
        basic_layout(self)

    def generate(self):
        # 生成 conanautotoolsdeps.sh（含 libnfc + libusb-compat + libusb 的
        # CPPFLAGS/LDFLAGS/LIBS 传递 flags），供 build() 编译 C 测试程序时注入。
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
        self.run('"%s"' % test_bin, env="conanrun")

        # 2. 通用消费者冒烟测试：真实执行被测包二进制
        pkg = self.dependencies["libnfc-tools"]
        bin_dir = os.path.join(pkg.package_folder, "bin")
        script = os.path.join(self.source_folder, "run_nfc_tools_test.sh")
        # HMDFS 上 chmod +x 不生效（E011），经 sh 解释器调用，不依赖执行位
        self.run('sh "%s" "%s"' % (script, bin_dir), env="conanrun")
