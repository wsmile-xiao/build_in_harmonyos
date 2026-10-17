#!/usr/bin/env python3
"""Compile and run a tinyusb consumer against the OHOS package."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class TinyusbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        tinyusb = self.dependencies["tinyusb"]
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        source = os.path.join(self.source_folder, "test_tinyusb.c")
        executable = os.path.join(self.build_folder, "test_tinyusb")

        # tinyusb 是源码库，头文件自 src/ 根目录起相对包含（"common/..."），
        # 所以只需要包内的 include 根。链接期需要消费侧补齐 template 端口与
        # OSAL 的 3 个钩子 + 本应用启用的类回调，全部写在 test_tinyusb.c 里。
        self.run(
            '"{}" -std=gnu11 "{}" -I"{}" -L"{}" -ltinyusb -o "{}"'.format(
                cc,
                source,
                os.path.join(tinyusb.package_folder, "include"),
                os.path.join(tinyusb.package_folder, "lib"),
                executable,
            ),
            env="conanbuild",
        )
        if can_run(self):
            self.run('"{}"'.format(executable), env="conanrun")
