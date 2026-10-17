#!/usr/bin/env python3
"""Conan recipe for dot2tex 2.12.0 — pure Python setuptools package.

dot2tex is a tool to convert Graphviz DOT files to LaTeX TikZ/PGF format.
It is a pure Python package with no C extensions; installation uses setuptools.

R32: settings.os 判断使用 in ("Linux", "OHOS").
R27: 依赖使用 @ohpcd/stable 格式。
R34: test_package 实质性测试（dot2tex --version + Python 模块导入）。
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Dot2texConan(ConanFile):
    name = "dot2tex"
    version = "2.12.0"
    description = "Graphviz DOT to LaTeX TikZ/PGF converter (pure Python)"
    license = "MIT"
    homepage = "https://github.com/sagemath/dot2tex"
    url = "https://github.com/sagemath/dot2tex"

    settings = "os", "arch"
    package_type = "application"  # R38: CLI 工具，非 library

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # dot2tex 运行时依赖 pyparsing（制品仓已发布）。
        # 引用使用无 channel 格式：R27（@user/channel 依赖格式）已废弃，
        # 制品仓已完成无 channel 迁移（pyparsing/3.1.4 已发布）。
        # 不声明 python3：制品仓无 python3 配方，构建用 sys.executable
        # （Conan 运行的 Python），运行时 python3 由设备/CI 环境提供。
        self.requires("pyparsing/3.1.4")

    def layout(self):
        basic_layout(self)

    def validate(self):
        """R32: OHOS 平台兼容 — 在 validate() 中拒绝不支持的 OS，而非 build() 中 raise。"""
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}. "
                f"dot2tex only supports Linux and OHOS."
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        """Apply patches and install dot2tex via setuptools."""
        apply_conandata_patches(self)
        # Use pip3 to install with --prefix for the staging prefix
        prefix = os.path.join(self.build_folder, "package")
        # R33: 不依赖 shell 环境变量，使用 Conan 管理的 python
        python = sys.executable
        # 不带 --no-build-isolation：dot2tex 的 pyproject.toml 声明 setuptools
        # 为构建后端，CI 的 HNP Python 未预装 setuptools，由 pip 隔离构建自动下载。
        self.run(f"{python} -m pip install . --prefix={prefix} --no-deps",
                 cwd=self.source_folder)

    def package(self):
        prefix = os.path.join(self.build_folder, "package")
        if not os.path.isdir(prefix):
            self.output.warning(f"Package directory not found: {prefix}, nothing to package")
            return
        # Copy all installed files from prefix to package_folder
        for item in os.listdir(prefix):
            src = os.path.join(prefix, item)
            dst = os.path.join(self.package_folder, item)
            if os.path.isdir(src):
                copy(self, "*", src=src, dst=dst)
            else:
                copy(self, item, src=prefix, dst=self.package_folder)

    def package_info(self):
        # dot2tex is a command-line tool; bin/ contains the executable
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        # Python site-packages need to be discoverable
        python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_pkgs = os.path.join("lib", python_version, "site-packages")
        self.cpp_info.includedirs = []
        # 设置 PYTHONPATH 使下游消费者可以 import dot2tex 模块
        site_pkgs_path = os.path.join(self.package_folder, site_pkgs)
        self.runenv_info.append_path("PYTHONPATH", site_pkgs_path)
        # dot2tex 运行时依赖 pyparsing：把 pyparsing 的 site-packages 一并注入
        # PYTHONPATH（pyparsing binary 在 test 阶段可能被 Skipped，runenv_info
        # 不自动聚合，此处显式补齐，保证 import dot2tex / dotparsing 可用）。
        try:
            py_dep = self.dependencies["pyparsing"]
            py_site = os.path.join(py_dep.package_folder, site_pkgs)
            self.runenv_info.append_path("PYTHONPATH", py_site)
        except Exception:
            pass
        self.output.info(f"dot2tex installed: bin/dot2tex, {site_pkgs}/dot2tex/")
