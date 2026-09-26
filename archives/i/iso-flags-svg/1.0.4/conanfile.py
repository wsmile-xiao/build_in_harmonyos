#!/usr/bin/env python3
"""Conan recipe for iso-flags-svg 1.0.4 — ISO 3166-1 国家/地区 SVG 旗帜数据包。

上游: https://github.com/linuxmint/iso-country-flags-svg-collection
      （版本号沿用 https://github.com/linuxmint/flags 的 v1.0.4 tag）
源码分发: https://deb.debian.org/debian/pool/main/i/iso-flags-svg/iso-flags-svg_1.0.4.orig.tar.gz
（本配方走清华 TUNA 镜像同一份文件，sha256 与 Debian .dsc 的 Checksums-Sha256 一致）

这是一个**纯数据包**：没有任何编译步骤。安装内容为两套旗帜：

    share/iso-flags-svg/country-4x3/      262 个 SVG，4:3 矩形旗（640x480）
    share/iso-flags-svg/country-squared/  253 个 SVG，1:1 方形旗（512x512）
    share/iso-flags-svg/iso-3166-1.csv    ISO 3166-1 alpha-2 索引（248 个国家/地区，6 列）
    share/iso-flags-svg/iso-3166-1.json   同一索引的 JSON 形态（248 个键）

文件名即小写的 alpha-2 代码（`cn.svg` = 中国）。除 248 个主权国家/地区外，
上游还带少量非国家旗帜（`eu`、`_united_nations`、`_scotland`、`_wales` 等），
两套目录的富余条目并不相同，测试用例对此逐一核对。

License: public-domain（上游无 LICENSE 文件，随包附带 COPYRIGHT.txt 记录
         Debian 版权文件中的公有领域声明）
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, export_conandata_patches, apply_conandata_patches, get
from conan.tools.layout import basic_layout


class IsoFlagsSvgConan(ConanFile):
    name = "iso-flags-svg"
    version = "1.0.4"
    description = ("ISO 3166-1 country flag SVG collection — 248 alpha-2 flags in "
                   "4:3 and 1:1 aspect ratios, with CSV/JSON index")
    license = "public-domain"
    homepage = "https://github.com/linuxmint/iso-country-flags-svg-collection"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 纯数据包：无编译、无 settings，产物与架构无关（同 adwaita-fonts-mono /
    # papirus-icon / ieee-data 的形态）。
    package_type = "unknown"

    # 上游 orig tarball 里没有 LICENSE/COPYING（Debian 的版权声明只在
    # debian/copyright 里），因此随配方一起导出 COPYRIGHT.txt。
    exports_sources = "COPYRIGHT.txt"

    no_copy_source = True

    _data_subdir = os.path.join("share", "iso-flags-svg")

    # 两套旗帜目录（目录名 → 文件名宽高比，用于测试断言）
    _FLAG_DIRS = ("country-4x3", "country-squared")

    # 两套目录中包含的非 ISO 3166-1 条目（上游自带，逐字固定，便于回归比对）
    _EXTRA_FLAGS = {
        "country-4x3": ("_basque", "_catalonia", "_earth_pernefeldt", "_galicia",
                        "_generic", "_olympic", "_scotland", "_united_nations",
                        "_wales", "brl", "eo", "eu", "ss", "zz"),
        "country-squared": ("brl", "eo", "eu", "ss", "zz"),
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # 没有编译器参与，但必须确认数据真的下载到了 —— 一个"下载失败却仍然
        # 打包成功"的空数据包比构建失败更危险。
        for name in self._FLAG_DIRS:
            directory = os.path.join(self.source_folder, "svg", name)
            if not os.path.isdir(directory):
                raise ConanException(
                    f"upstream flag directory missing: svg/{name}")

        for fn in ("iso-3166-1.csv", "iso-3166-1.json"):
            path = os.path.join(self.source_folder, fn)
            if not os.path.isfile(path) or os.path.getsize(path) == 0:
                raise ConanException(f"upstream index file missing or empty: {fn}")

        total = sum(len(os.listdir(os.path.join(self.source_folder, "svg", name)))
                    for name in self._FLAG_DIRS)
        self.output.info(f"iso-flags-svg: {total} SVG flags in {len(self._FLAG_DIRS)} sets")

    def package(self):
        data_dir = os.path.join(self.package_folder, self._data_subdir)

        for name in self._FLAG_DIRS:
            copy(self, "*.svg", src=os.path.join(self.source_folder, "svg", name),
                 dst=os.path.join(data_dir, name))

        copy(self, "iso-3166-1.csv", src=self.source_folder, dst=data_dir)
        copy(self, "iso-3166-1.json", src=self.source_folder, dst=data_dir)

        copy(self, "COPYRIGHT.txt", src=self.export_sources_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 纯数据包：没有库、没有可执行文件、没有头文件。
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

        self.cpp_info.resdirs = [self._data_subdir]

        data_dir = os.path.join(self.package_folder, self._data_subdir)
        self.buildenv_info.define("ISO_FLAGS_SVG_DIR", data_dir)
        self.runenv_info.define("ISO_FLAGS_SVG_DIR", data_dir)
        self.output.info(f"ISO_FLAGS_SVG_DIR={data_dir}")
