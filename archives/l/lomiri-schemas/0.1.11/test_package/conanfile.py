#!/usr/bin/env python3
"""Conan test_package — lomiri-schemas 0.1.11（R34 真实产物 + 鸿蒙特有功能断言）。

lomiri-schemas 是纯数据包，没有可链接的产物，可验证物是安装出来的 schema /
D-Bus 接口 XML / polkit 数据 / pkg-config 元数据。断言脚本在 OHOS 目标上实跑
（本仓 CI worker 为 OHOS aarch64，native 构建），并用 glib 包自带的
glib-compile-schemas 对 schema 目录做 --strict --dry-run 全量校验——这是
GSettings 运行期真正接受的模式合法性检查。
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import cross_building


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # glib 是 openvi 式的传递依赖：不显式声明时 package_folder 为 None，
        # 拼不出 <glib>/bin/glib-compile-schemas；显式声明后 conanrun 也会带上
        # glib 的 runenv（LD_LIBRARY_PATH），schema 编译才能真正跑起来。
        self.requires("glib/2.88.3")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验包存在")
            return
        dep = self.dependencies["lomiri-schemas"]
        glib = self.dependencies["glib"]
        script = os.path.join(self.source_folder, "test_lomiri_schemas.py")
        self.run(
            f'{sys.executable} "{script}" "{dep.package_folder}" '
            f'"{glib.package_folder}"',
            env="conanrun",
        )
