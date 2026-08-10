#!/usr/bin/env python3
"""Conan test_package — Adobe Source Han Sans CN.

Run test_fonts.py to verify that font files were installed correctly.
"""
import os
import sys

from conan import ConanFile


class AdobeSourceHanSansCNTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        pass

    def build(self):
        pass

    def test(self):
        # resdirs[0] 已解析为 <package_folder>/fonts
        font_dir = self.dependencies["adobe-source-han-sans-cn"].cpp_info.resdirs[0]
        # self.run() 在 build_folder 执行，脚本须用 source_folder 构造绝对路径
        test_script = os.path.join(self.source_folder, "test_fonts.py")
        self.run(f'{sys.executable} "{test_script}" {font_dir}', env="conanrun")
