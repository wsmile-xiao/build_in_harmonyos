#!/usr/bin/env python3
"""Conan test_package for file-sharedir 1.118 — consumer check (R34 真实 API).

通过 test_file_sharedir.py 驱动 perl 消费者测试，载入**已打包**的
File::ShareDir 并真实调用 dist_dir/dist_file/module_dir/module_file。

env="conanrun" 注入是必需的：本包 package_info() 与依赖的 PERL5LIB 都由
runenv_info 声明，裸 subprocess 会丢失该注入（参见 perl-uri 先例的
FileNotFoundError 教训）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class FileSharedirTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["file-sharedir"].package_folder
        # 安装前缀随 perl 构建而异 → 遍历定位 File/ShareDir.pm，
        # 返回的 site 即包含该相对路径的 perl lib 根
        rel = os.path.join("File", "ShareDir.pm")
        site = None
        for root, _dirs, _files in os.walk(pkg):
            if os.path.isfile(os.path.join(root, rel)):
                site = root
                break
        if not site:
            raise ConanException("File/ShareDir.pm not found in package")

        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_file_sharedir.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_file_sharedir.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
