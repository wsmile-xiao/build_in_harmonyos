#!/usr/bin/env python3
"""Conan recipe for ieee-data 20260625 — IEEE 注册管理机构公开数据表。

上游（Debian 原生包）: https://packages.debian.org/source/sid/ieee-data
源码分发: https://deb.debian.org/debian/pool/main/i/ieee-data/ieee-data_20260625.tar.xz
（本配方走清华 TUNA 镜像，sha256 与 Debian .dsc 的 Checksums-Sha256 一致）

ieee-data 提供 IEEE 公共注册管理机构（Registration Authority）的全部公开
分配表，是 MAC 地址厂商查询（oui、Wireshark、arp-scan、netdiscover 等）
的公共数据源：

    oui.txt / oui.csv       MA-L  24 bit  (6 hex)  OUI 注册表
    mam.txt / mam.csv       MA-M  28 bit  (7 hex)  中型注册表
    oui36.txt / oui36.csv   MA-S  36 bit  (9 hex)  小型注册表
    iab.txt / iab.csv       IAB   36 bit  (9 hex)  独立地址块
    .lastupdate             数据刷新时间戳（Unix epoch）

这是一个**纯数据包**：没有任何编译步骤、没有库、没有可执行产物。
因此本配方不做交叉编译，只做「下载 → 校验 → 安装数据表 → 自检」。
上游 tarball 里的 `Makefile` 只有 `all:`（空）与 `install:`（拷贝数据文件），
Debian 的 `update-ieee-data` 是 /usr/sbin 下的运行时联网刷新脚本，本包不安装
（原因见 notes.md 与 PR 说明）。

License: WTFPL-2.0（Debian 维护部分）+ IEEE 数据表原始条款
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, export_conandata_patches, apply_conandata_patches, get
from conan.tools.layout import basic_layout


class IeeeDataConan(ConanFile):
    name = "ieee-data"
    version = "20260625"
    description = ("IEEE registration authority public data — OUI/MA-L, MA-M, MA-S "
                   "and IAB assignment registries for MAC address vendor lookup")
    license = "WTFPL-2.0"
    homepage = "https://packages.debian.org/source/sid/ieee-data"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 纯数据包：无编译、无 settings 依赖，产物与架构无关。
    # （与已合入的 adwaita-fonts-mono / papirus-icon 同形态，R32 对纯数据包跳过
    #  settings.os 检查。）
    package_type = "unknown"

    no_copy_source = True

    # 数据表相对 package_folder 的安装目录
    _data_subdir = os.path.join("share", "ieee-data")

    # IEEE 四个注册表，每个都有 .txt（人读）与 .csv（机读）两种形态
    _REGISTRIES = ("oui", "mam", "oui36", "iab")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # 没有编译器参与，但必须确认上游四个注册表确实下载到了 ——
        # 一个"下载失败却仍然打包成功"的空数据包比构建失败更危险。
        expected = [f"{name}{ext}" for name in self._REGISTRIES
                    for ext in (".txt", ".csv")]
        expected.append(".lastupdate")

        missing = [fn for fn in expected
                   if not os.path.isfile(os.path.join(self.source_folder, fn))]
        if missing:
            raise ConanException(
                f"IEEE registration data missing from the upstream tarball: {missing}")

        empty = [fn for fn in expected
                 if os.path.getsize(os.path.join(self.source_folder, fn)) == 0]
        if empty:
            raise ConanException(f"IEEE registration data files are empty: {empty}")

        total = sum(os.path.getsize(os.path.join(self.source_folder, fn))
                    for fn in expected)
        self.output.info(f"ieee-data: {len(expected)} data files, {total} bytes total")

    def package(self):
        data_dir = os.path.join(self.package_folder, self._data_subdir)

        for name in self._REGISTRIES:
            copy(self, f"{name}.txt", src=self.source_folder, dst=data_dir)
            copy(self, f"{name}.csv", src=self.source_folder, dst=data_dir)
        # 点开头文件必须显式拷贝："*" 通配在部分 Conan 版本的 copy() 里不覆盖
        # 以 "." 开头的文件。
        copy(self, ".lastupdate", src=self.source_folder, dst=data_dir)

        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 纯数据包：没有库、没有可执行文件、没有头文件。
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

        # 消费方（fc-list 式的数据查找、ArpScan 式的厂商库构建）通过 resdirs
        # 与预定义环境变量定位数据目录。
        self.cpp_info.resdirs = [self._data_subdir]

        data_dir = os.path.join(self.package_folder, self._data_subdir)
        self.buildenv_info.define("IEEE_DATA_DIR", data_dir)
        self.runenv_info.define("IEEE_DATA_DIR", data_dir)
        self.output.info(f"IEEE_DATA_DIR={data_dir}")
