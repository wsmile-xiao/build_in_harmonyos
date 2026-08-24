#!/usr/bin/env python3
"""Conan recipe for buildessential 1.0.0 — Chef cookbook（Opscode build-essential）。

上游：https://supermarket.chef.io/cookbooks/build-essential（v1.0.0）
本质：Chef 配置管理配方——纯 Ruby DSL 脚本（metadata.rb + recipes/default.rb），
      无编译、无产物、无运行库——按配置/脚本分发打包。
消费测试：ruby -c 验证 Ruby DSL 语法（OHOS 有 ruby 3.4.5）+ 文件完整性。
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class BuildessentialConan(ConanFile):
    name = "buildessential"
    version = "1.0.0"
    description = "build-essential Chef cookbook — Installs C compiler / build tools (Ruby DSL)"
    license = "Apache-2.0"
    homepage = "https://supermarket.chef.io/cookbooks/build-essential"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        # Supermarket download URL 无 .tar.gz 扩展名——显式指定 filename
        # 让 conan get() 按 tar.gz 解压（否则 BadZipFile 判为 zip 失败）
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="build-essential-1.0.0.tar.gz")

    def build(self):
        # 纯 Ruby DSL 配置脚本——无编译。上游无独立测试套件
        # （cookbook 测试依赖 Chef 生态 kitchen/chefspec——1.0.0 无测试目录）——
        # 语法验证放消费测试（ruby -c）。
        pass

    def package(self):
        # 复制 cookbook 全部文件（metadata.rb/metadata.json/README.md/recipes/）
        copy(self, "*", src=self.source_folder, dst=self.package_folder,
             excludes=("*.tar.gz",))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
