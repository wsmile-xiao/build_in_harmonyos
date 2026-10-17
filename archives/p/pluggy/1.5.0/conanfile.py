#!/usr/bin/env python3
"""Conan recipe — pluggy 1.5.0 (setuptools pure Python src layout).

pluggy is a minimalist production ready plugin system, the core framework
used by pytest/tox/devpi. Pure-Python src layout (src/pluggy/), built with
setuptools + setuptools-scm (sdist pins __version__ = '1.5.0').

R32: settings.os 判断使用 in ("Linux", "OHOS").
R34: test_package 实质性测试（模块导入 + HookspecMarker/HookimplMarker/PluginManager/hook 调用）.
R33: build() 不依赖 shell 环境变量，使用 sys.executable（Conan 运行时 Python）.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class PluggyConan(ConanFile):
    name = "pluggy"
    version = "1.5.0"
    description = "plugin and hook calling mechanisms for python"
    license = "MIT"
    homepage = "https://github.com/pytest-dev/pluggy"
    url = "https://github.com/pytest-dev/pluggy"

    settings = "os", "arch"
    package_type = "library"
    # Conan 2.x 要求 library 类型必须声明 shared option（纯 Python 包，固定 False）
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        pass

    # 无外部 Conan 依赖：纯 Python 库，构建用 sys.executable（Conan 运行的
    # Python），运行时 python3 由设备/CI 环境提供（同 pyparsing/cfgv 惯例）。

    def layout(self):
        basic_layout(self)

    def validate(self):
        """R32: OHOS 平台兼容 — 在 validate() 中拒绝不支持的 OS。"""
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}. "
                f"pluggy only supports Linux and OHOS."
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        """Install pluggy via pip from source (local build, no pre-built wheel)."""
        prefix = os.path.join(self.build_folder, "package")
        # R33: 不依赖 shell 环境变量，使用 Conan 管理的 python
        python = sys.executable
        # pip install . builds from source (setup.py + setup.cfg + pyproject.toml).
        # --no-deps: pluggy has no runtime deps (only dev: pytest, pytest-benchmark).
        # 不带 --no-build-isolation: 构建 Python 未预装 setuptools/setuptools-scm,
        # 让 pip 自动创建隔离环境并从配置的 pypi.cnb.cool 源下载构建依赖
        # (同 pyparsing/cfgv 方案).
        self.run(
            f"{python} -m pip install . --prefix={prefix} --no-deps",
            cwd=self.source_folder,
        )

    def package(self):
        prefix = os.path.join(self.build_folder, "package")
        if not os.path.isdir(prefix):
            raise ConanException(
                f"Package directory not found: {prefix}, nothing to package"
            )
        for item in os.listdir(prefix):
            src = os.path.join(prefix, item)
            dst = os.path.join(self.package_folder, item)
            if os.path.isdir(src):
                copy(self, "*", src=src, dst=dst)
            else:
                copy(self, item, src=prefix, dst=self.package_folder)

    def package_info(self):
        # pluggy is a pure Python library (src/pluggy/ package);
        # provide site-packages path via PYTHONPATH for consumers.
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_pkgs_path = os.path.join(
            self.package_folder, "lib", python_version, "site-packages"
        )
        # Conan 2.x runenv_info.append_path — 路径类环境变量
        self.runenv_info.append_path("PYTHONPATH", site_pkgs_path)
        self.output.info(f"pluggy installed: {site_pkgs_path}/pluggy/")
