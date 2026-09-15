#!/usr/bin/env python3
"""Conan recipe for pari-seadata 20090618 (鸿蒙 PC 原生构建).

pari-seadata 是 **纯数据包**（Debian: Architecture: all）：它只是 PARI/GP 的
`ellsea`/`ellap` 所需的模多项式数据表（p < 500 的 sea<p> 文件，源自 ECHIDNA
数据库，David R. Kohel 计算）。

上游没有任何可编译代码、没有 configure/Makefile/CMake、也没有自动化测试套件：
- `seadata.tgz` 内 53 个条目全是 `data/seadata/sea<p>`（ASCII，GP 向量文本）+ README；
- `debian/rules` 的 build 目标只 `touch build-stamp`，install 只 `dh_install`
  拷数据 + `gzip`（无 check/test 目标）。

所以本 recipe 的 "build" 是空操作，"install" 就是把 seadata/ 目录落到包内 res/ 下，
并由下游 gp 通过 PARI 的 share_path 读取。上游无测试 → 测试入口核验见 test_package/
MANIFEST.yml；test_package 用内容指纹（文件数 + 拼接 sha256 + GP 格式）实质校验
打包数据（R34），不能替代也不谎称上游测试。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches, get)


class PariSeadataConan(ConanFile):
    name = "pari-seadata"
    version = "20090618"
    description = ("PARI/GP modular polynomial data (seadata) for ellsea/ellap, "
                   "prime level p < 500 (2009-06-18 release)")
    license = "GPL-2.0-or-later"
    homepage = "https://pari.math.u-bordeaux.fr/packages.html#seadata"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    # 纯数据包：不产出 .so/.a，也不产出可执行文件。与已入库的 ca-certificates 同型
    # （application + commands.json binary:false），确保 conan create 真正执行 package()，
    # 产物 res/ 由 test_package 的内容级校验实质覆盖。
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    # R32: settings.os 判断用 in (...)，不能 == "Linux"
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pari-seadata is a data package; supported on Linux/OHOS")

    def export_sources(self):
        # 本包无补丁；标准补丁钩子，export_conandata_patches/apply_conandata_patches
        # 在 conandata 无 patches 段时为安全的空操作（与仓库既有 data-only 配方形态一致）。
        export_conandata_patches(self)

    def layout(self):
        # 让 self.source_folder 直接指向解包根（strip_root 后），路径可预测
        self.folders.source = "."

    def source(self):
        # 上游官方源（R39）：seadata.tgz，顶层目录 data/ 被 strip_root 去掉，
        # 得到 <src>/seadata/{sea0,sea2,...,README}
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯数据包：无 configure / 无编译 / 无链接 / 无测试。
        # 上游 debian/rules 的 build 目标亦仅 `touch build-stamp`。此处无补丁可应用，
        # apply_conandata_patches 在无 patches 段时空操作（保留以对齐配方标准形态）。
        apply_conandata_patches(self)

    def package(self):
        # 与 Debian `dh_install seadata /usr/share/pari` 对应：落到包内 res 树。
        # 保留上游原始未压缩 sea<p> 文件（PARI 可直读；不引入 gzip 构建期工具）。
        src = os.path.join(self.source_folder, "seadata")
        dst = os.path.join(self.package_folder, "res", "pari", "seadata")
        copy(self, "*", src=src, dst=dst)
        # 许可证随附（README 内含 GPL 声明；上游 tarball 无独立 COPYING 文件）
        copy(self, "README", src=src, dst=dst)

    def package_info(self):
        # 无库、无二进制；通过 cpp_info.resdirs 暴露数据根（Conan 2 原生，避免
        # user_info 的 1.x 弃用告警）。下游 gp 用 package_folder + resdirs 拼出
        #   <pkg>/res/pari/seadata 指给 PARI 的 seadata 目录。
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["res"]
        # 记一个自定义属性，方便下游直接取相对路径（get_property）。
        self.cpp_info.set_property("pari:seadata_rel", os.path.join(
            "res", "pari", "seadata"))
