#!/usr/bin/env python3
"""debian-astro 5 test_package —— 纯数据包，无需编译。"""

import os
import sys

from conan import ConanFile


class BlendTestConan(ConanFile):
    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["debian-astro"]
        package_folder = dep.package_folder

        # ① 完整消费者用例（平台 rule12）：按 tasksel/blends 语义把 blend 消费一遍
        #    （desc 的 Key/Parent 任务树 → tasks/<键> 的 Depends∪Recommends/X-Depends）
        consumer = os.path.join(self.source_folder, "consumer_blend.py")
        self.run(f"{sys.executable} {consumer} {package_folder}")

        # ② 适配自检（M=13，非上游用例；上游 N=0）
        script = os.path.join(self.source_folder, "test_blend.py")
        self.run(f"{sys.executable} {script} {package_folder}")
