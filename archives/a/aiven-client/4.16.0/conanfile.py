#!/usr/bin/env python3
"""Conan recipe — aiven-client 4.16.0 (hatchling pure Python src layout).

aiven-client (avn) is the official command-line client for Aiven.
Pure-Python package layout (aiven/), built with hatchling + hatch-vcs.
The sdist ships a generated aiven/client/version.py pinning 4.16.0.

R32: settings.os 判断使用 in ("Linux", "OHOS").
R34: test_package 实质性测试（模块导入 + AivenClient/argx/pretty/speller 调用）.
R33: build() 不依赖 shell 环境变量，使用 sys.executable（Conan 运行时 Python）.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AivenClientConan(ConanFile):
    name = "aiven-client"
    version = "4.16.0"
    description = "Aiven.io client library / command-line client"
    license = "Apache-2.0"
    homepage = "https://github.com/aiven/aiven-client"
    url = "https://github.com/aiven/aiven-client"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "library"
    # 纯 Python 包无编译器/构建类型依赖，但 OHOS profile 的 L0p 门禁强制要求
    # settings 四项齐全（os/compiler/build_type/arch），对齐 arno-iptables-firewall
    # /aribb24/kcrash 等已通过 CI 的非 C++ 包惯例。compiler/build_type 不会在
    # build() 中被实际使用（pip install 不读 settings.compiler），仅满足门禁。
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    # 无补丁：aiven-client 4.16.0 sdist 已含生成文件 version.py，可直接构建。
    # patches 声明保留为空（conandata.yml patches: []），apply_conandata_patches 为空操作。
    # 无外部 Conan 依赖：纯 Python 库，构建用 sys.executable（Conan 运行的
    # Python），运行时 python3 由设备/CI 环境提供（同 pluggy/cfgv 惯例）。
    # 运行时 Python 依赖：requests, requests-toolbelt, certifi——由设备端
    # pip 环境或上层应用负责提供（鸿蒙 PC 自带 Python 3.12 + pip）。

    def layout(self):
        basic_layout(self)

    def validate(self):
        """R32: OHOS 平台兼容 — 在 validate() 中拒绝不支持的 OS。"""
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}. "
                f"aiven-client only supports Linux and OHOS."
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        """Install aiven-client via pip from source (local build, no pre-built wheel)."""
        apply_conandata_patches(self)
        prefix = os.path.join(self.build_folder, "package")
        # R33: 不依赖 shell 环境变量，使用 Conan 管理的 python
        python = sys.executable
        # pip install . builds from source (pyproject.toml + hatchling).
        # 带运行时依赖（requests/requests-toolbelt/certifi）由 pip 从配置的
        # pypi.cnb.cool 镜像自动解析安装，确保 test_package 运行时导入链可用
        # （aiven.client.__init__ → client.py → requests_toolbelt）。
        # 不带 --no-build-isolation: 让 pip 自动创建隔离环境并从配置的
        # pypi.cnb.cool 源下载构建依赖 (hatchling/hatch-vcs，同 pluggy 方案).
        self.run(
            f"{python} -m pip install . --prefix={prefix}",
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
        # aiven-client is a pure Python library (aiven/ package);
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
        self.output.info(f"aiven-client installed: {site_pkgs_path}/aiven/")
