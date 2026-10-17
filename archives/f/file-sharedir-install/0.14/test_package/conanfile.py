#!/usr/bin/env python3
"""Conan test_package for file-sharedir-install 0.14 — consumer check (R34 真实 API).

通过 test_file_sharedir_install.py 驱动 perl 加载 <pkg> 中的
File::ShareDir::Install，并真实执行「登记共享目录 → 生成 Makefile → make →
校验 blib 产物」的完整消费者流程。env="conanrun" 注入 is required（裸
subprocess 会丢失 conanrun 环境注入，参见 perl-uri 先例的 FileNotFoundError 教训）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class FileSharedirInstallTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["file-sharedir-install"].package_folder
        # 安装前缀随 perl 构建而异 → 遍历定位 File/ShareDir/Install.pm。
        # 模块在 <site>/File/ShareDir/Install.pm，故 site 需上溯两级
        # （不可返回末级目录，否则 -I 指向错误层级）。
        site = None
        for root, _dirs, files in os.walk(pkg):
            if "Install.pm" in files and root.endswith(
                    os.path.join("File", "ShareDir")):
                site = os.path.dirname(os.path.dirname(root))
                break
        if not site:
            raise ConanException("File/ShareDir/Install.pm not found in package")

        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_file_sharedir_install.py")
        if not os.path.isfile(test_script):
            raise ConanException(
                f"test_file_sharedir_install.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
