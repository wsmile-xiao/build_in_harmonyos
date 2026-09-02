#!/usr/bin/env python3
"""Conan recipe — avahi-nftrules 0.9_rc5 (data package)"""

from conan import ConanFile
from conan.tools.files import copy, download
import os

class AvahiNftrulesConan(ConanFile):
    name = "avahi-nftrules"
    version = "0.9_rc5"
    description = "nftables ruleset for Avahi mDNS/DNS-SD"
    license = "LGPL-2.1-or-later"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://avahi.org"
    topics = ("avahi", "mdns", "dns-sd", "nftables", "firewall")
    
    # 数据文件包，不是库也不是可执行程序
    settings = "os", "arch", "compiler", "build_type"
    
    def export_sources(self):
        copy(self, "conandata.yml", self.recipe_folder, self.export_sources_folder)
    
    def source(self):
        # 直接下载 nftables 规则文件
        download(self, **self.conan_data["sources"][self.version], 
                 filename="50_avahi.nft")
    
    def build(self):
        # 配置文件包，无需编译
        pass
    
    def package_id(self):
        # 配置文件包，与编译器/build_type 无关
        del self.info.settings.compiler
        del self.info.settings.build_type
    
    def package(self):
        # 安装到标准位置
        copy(self, "50_avahi.nft",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "nftables.avail"),
             keep_path=False)
    
    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        
        # 设置数据目录
        nft_dir = os.path.join(self.package_folder, "share", "nftables.avail")
        self.runenv_info.define_path("AVAHI_NFT_RULES", nft_dir)
