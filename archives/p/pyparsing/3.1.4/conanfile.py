#!/usr/bin/env python3
"""Conan recipe — pyparsing 3.1.4 (setuptools).

Pure Python parsing library; no C extensions. Uses setuptools install.
R32: settings.os 判断使用 in ("Linux", "OHOS").
R34: test_package 实质性测试（模块导入 + 基本解析功能）.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class PyparsingConan(ConanFile):
    name = "pyparsing"
    version = "3.1.4"
    description = "Python parsing library for DOT syntax and more (pure Python)"
    license = "MIT"
    homepage = "https://github.com/pyparsing/pyparsing"
    url = "https://github.com/pyparsing/pyparsing"

    settings = "os", "arch"
    package_type = "library"
    # Conan 2.x 要求 library 类型必须声明 shared option（纯 Python 包，固定 False）
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        pass

    # 无外部 Conan 依赖：纯 Python 库，构建用 sys.executable（Conan 运行的
    # Python），运行时 python3 由设备/CI 环境提供（同 cpython-tkinter 惯例）。
    # 注：R27（@user/channel 依赖格式）已废弃；制品仓无 python3/3.12.9 配方。

    def layout(self):
        basic_layout(self)

    def validate(self):
        """R32: OHOS 平台兼容 — 在 validate() 中拒绝不支持的 OS。"""
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}. "
                f"pyparsing only supports Linux and OHOS."
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        """Install pyparsing via pip."""
        prefix = os.path.join(self.build_folder, "package")
        # R33: 不依赖 shell 环境变量，使用 Conan 管理的 python
        python = sys.executable
        # 不带 --no-build-isolation：pyparsing 3.1.4 的 pyproject.toml 声明
        # flit_core 为构建后端，CI 的 HNP Python 未预装 flit_core，
        # 让 pip 自动创建隔离环境并下载构建依赖。
        self.run(f"{python} -m pip install . --prefix={prefix} --no-deps",
                 cwd=self.source_folder)

    def package(self):
        prefix = os.path.join(self.build_folder, "package")
        if not os.path.isdir(prefix):
            raise ConanException(f"Package directory not found: {prefix}, nothing to package")
        for item in os.listdir(prefix):
            src = os.path.join(prefix, item)
            dst = os.path.join(self.package_folder, item)
            if os.path.isdir(src):
                copy(self, "*", src=src, dst=dst)
            else:
                copy(self, item, src=prefix, dst=self.package_folder)

    def package_info(self):
        # pyparsing is a library; provide site-packages path
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_pkgs = os.path.join("lib", python_version, "site-packages")
        # 设置 PYTHONPATH 使下游消费者和 test_package 可以 import pyparsing
        # 使用 Conan 2.x runenv_info.append_path（路径类环境变量应用 append_path）
        site_pkgs_path = os.path.join(self.package_folder, site_pkgs)
        self.runenv_info.append_path("PYTHONPATH", site_pkgs_path)
        self.cpp_info.includedirs = []
        self.output.info(f"pyparsing installed: {site_pkgs}/pyparsing/")
