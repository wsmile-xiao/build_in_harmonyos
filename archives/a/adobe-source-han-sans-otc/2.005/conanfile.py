#!/usr/bin/env python3
"""Conan recipe — Adobe Source Han Sans OTC (思源黑体 OpenType Collection 合集).

纯字体数据包，无需编译，仅下载并安装 OTC/OTF 字体文件到系统字体目录。
OTC 为多语言 OpenType Collection（含 CN/TW/HK/JP/KR 全部语言）。
"""
from conan import ConanFile
from conan.tools.files import get, copy
import os


class AdobeSourceHanSansOTCConan(ConanFile):
    name = "adobe-source-han-sans-otc"
    version = "2.005"
    description = "Adobe Source Han Sans OTC - 思源黑体 OpenType Collection 合集(全语言) Pan-CJK 无衬线字体"
    license = "OFL-1.1"
    homepage = "https://github.com/adobe-fonts/source-han-sans"
    url = ""

    settings = "os", "arch"

    def layout(self):
        pass

    def export_sources(self):
        pass

    def source(self):
        # 该 ZIP 根目录含多个条目(LICENSE.txt、OTC/、根级 .ttc 文件),不能 strip_root
        get(self, **self.conan_data["sources"], strip_root=False)

    def build(self):
        # 字体包无需编译
        pass

    def package(self):
        # 安装所有字体文件到 fonts/ 目录
        src_dir = self.source_folder
        font_exts = (".otf", ".ttf", ".otc", ".ttc")
        dest = os.path.join(self.package_folder, "fonts")
        installed = 0
        for root, dirs, files in os.walk(src_dir):
            for f in files:
                if f.lower().endswith(font_exts):
                    # keep_path=False 扁平化安装:ZIP 内 OTF/Japanese/ 等子目录
                    # 不保留,字体直接装入 fonts/ 供 test_package 非递归验证
                    copy(self, f, src=root, dst=dest, keep_path=False)
                    installed += 1
        self.output.info(f"Installed {installed} font files to {dest}")

    def package_info(self):
        # 字体包，无标准 cpp_info，标记 resdirs 供 test_package 验证
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["fonts"]
