#!/usr/bin/env python3
"""Conan test_package for dazz_db — runs the installed tools for real.

The suite lives in test_package/test.sh: it drives the 13 installed commands
through the data paths documented in the upstream README (simulated reads ->
DB/DAM -> round trips -> partition -> dust track -> quiva stream -> DBrm) and
asserts the output of every step, including byte identical round trips.  All
artefacts are written to the build folder, which layout() keeps separate from
the package source directory.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class DazzDbTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        bindir = os.path.join(
            self.dependencies["dazz_db"].package_folder, "bin")
        script = os.path.join(self.recipe_folder, "test.sh")
        self.run('sh "%s" "%s" "%s"' % (script, bindir, self.build_folder),
                 env="conanrun")
        # 消费者用例（与上游测试、鸿蒙专项适配测试分别计数）：
        # 模拟业务上层组件，仅通过包导出的公开 CLI 完成完整业务工作流。
        consumer = os.path.join(self.recipe_folder, "consumer.sh")
        self.run('sh "%s" "%s" "%s"' % (consumer, bindir, self.build_folder),
                 env="conanrun")