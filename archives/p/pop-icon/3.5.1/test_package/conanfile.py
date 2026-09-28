#!/usr/bin/env python3
"""pop-icon 3.5.1 test_package —— 纯资源包，无需编译。

验证逻辑全部放在独立的 test_pop_icon.py 里，本文件只负责：
  1) 通过 dependencies 拿到被测算包的真实 package_folder；
  2) 用当前 Python 解释器（Conan 自身的解释器）执行验证脚本。
"""

import os
import sys

from conan import ConanFile


class PopIconTestConan(ConanFile):
    # 资源包：无编译器、无 settings、无 build 步骤。

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["pop-icon"]
        package_folder = dep.package_folder
        icons_root = os.path.join(package_folder, "share", "icons")

        # ① 完整消费者用例（平台 rule12）：按 freedesktop 查找算法消费主题
        #    （XDG 契约定位 → index.theme 的 Directories/Size/Type → 按名+尺寸解析到实体文件）
        consumer = os.path.join(self.source_folder, "consumer_icontheme.py")
        self.run(f"{sys.executable} {consumer} {package_folder}")

        # ② 适配自检（M=35，非上游用例；上游 N=0）
        script = os.path.join(self.source_folder, "test_pop_icon.py")
        self.run(f"{sys.executable} {script} {icons_root} {package_folder}")
