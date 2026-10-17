#!/usr/bin/env python3
"""Conan recipe for ausweisapp-nftrules — 纯数据包：AusweisApp2 nftables 规则集。

ausweisapp-nftrules 是德国联邦身份证官方认证应用 AusweisApp2 的 nftables
防火墙规则集（放行 BundID AusweisApp2 通信端口 24727）。上游 AusweisApp
源码 tarball 内不含此规则文件——规则由 Alpine Linux aports 维护
（community/ausweisapp/ausweisapp.nft），本配方直接下载该单文件作为源码。
纯数据包，无编译；package() 把规则文件拷到 etc/nftables.d/。
package_type=application（数据/配置包形态，配套 commands.json R38）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import download, export_conandata_patches, apply_conandata_patches


class AusweisappNftrulesConan(ConanFile):
    name = "ausweisapp-nftrules"
    version = "2.5.1"
    package_type = "application"
    license = "EUPL-1.2"
    homepage = "https://www.ausweisapp.bund.de/"
    description = "ausweisapp-nftrules — AusweisApp2 nftables firewall ruleset (accept tcp dport 24727)"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # 单文件下载（非 tarball）：从 Alpine aports 获取规则文件
        download(self, self.conan_data["sources"]["url"],
                 filename="ausweisapp.nft", sha256=self.conan_data["sources"]["sha256"])

    def build(self):
        # 纯数据包——无编译
        apply_conandata_patches(self)  # 无补丁时空操作

    def package(self):
        src = os.path.join(self.source_folder, "ausweisapp.nft")
        if not os.path.isfile(src):
            raise ConanException(f"ausweisapp.nft not found in source: {src}")
        dst_dir = os.path.join(self.package_folder, "etc", "nftables.d")
        os.makedirs(dst_dir, exist_ok=True)
        shutil.copy2(src, os.path.join(dst_dir, "ausweisapp.nft"))

    def package_info(self):
        self.cpp_info.libs = []
