#!/usr/bin/env python3
"""Conan recipe for algotutor 0.8.6 — interactive algorithm animation (Perl/Tk).

algotutor 是纯 Perl 脚本程序（算法动画演示工具），无编译：主脚本 algotutor +
utilalgo/basic.pl + 算法模块（BST/Graph/Heap/RBTree/Vector 等 *.pm）+ dp/ graph/
数据目录。依赖 perl-Tk（GUI，上游已适配 804.036 built）。

OHOS 适配要点：
- CI worker 网络受限（无法访问 people.ofset.org，源码下载超时）→ 源码文本
  目录（src/，42 个文本文件）随 export_sources 提供，source() 复制，参照 lv 先例。
  （注意：不能用 tar.gz 二进制——gitcode PR diff 无法传输新增二进制补丁数据）
- 脚本 BEGIN 块按 $0 所在目录 push @INC，故主脚本与全部 .pm/.pl/dp/graph/data
  放在同一 package 目录下（bin/），require 即可解析（与上游 make dist 结构一致）。
- 上游 make test（12 个用例）全部调用 algotutor 主脚本，脚本无条件
  MainWindow->new（Tk GUI）→ 需要 X11 display server；OHOS headless 构建环境
  无 X server，无法运行（与 perl-tk 804.036 适配 notes 同因，跳过 GUI 测试）。
- 消费测试：perl -c 语法检查不依赖 Tk 的算法模块 + 数据文件存在性验证。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, export_conandata_patches
from conan.tools.layout import basic_layout


class AlgotutorConan(ConanFile):
    name = "algotutor"
    version = "0.8.6"
    description = "Interactive program for observing the intermediate steps of algorithms"
    license = "GPL-3.0-or-later"
    homepage = "http://people.ofset.org/~ckhung/p/algotutor/"
    url = ""  # CI fills this

    package_type = "application"

    # L0p: OHOS profile 需要全部四项 settings（git-who 修复先例）
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"algotutor {self.version} only supports Linux/OHOS, got os={self.settings.os}")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # 官方源 deb.debian.org 实测可达（HTTP 200）→ 不再 bundled 源码，
        # 直接走 conandata sources.url 官方下载（R39 官方源）
        export_conandata_patches(self)

    def source(self):
        # 官方 Debian orig tarball 下载解压（strip_root 剥掉 algotutor-0.8.6.orig/ 顶层）
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯 Perl 脚本程序，无编译 → build 段空操作
        pass

    def package(self):
        # 主脚本 + 全部模块 + 数据目录放到 bin/（脚本 BEGIN 按 $0 所在目录
        # push @INC，require "utilalgo"/"basic.pl"/"dp/lcs" 等在同一目录树即可解析）
        dst_bin = os.path.join(self.package_folder, "bin")
        for f in ("algotutor", "utilalgo", "basic.pl", "gen_at_graph"):
            copy(self, f, src=self.source_folder, dst=dst_bin)
        # 仅打包有引用者的 .pm（Line/Vector3 无任何 use/require 引用，已剔除）
        for pm in ("BST", "Board", "Collection", "Configurable", "DCEdge",
                   "Edge", "Graph", "Heap", "PQueue", "RBTree",
                   "RecCanvas", "RecDialog", "TreeNode", "Vector", "Vector2",
                   "Vertex"):
            copy(self, f"{pm}.pm", src=self.source_folder, dst=dst_bin)
        for sub in ("dp", "graph", "cgeom"):
            copy(self, "*", src=os.path.join(self.source_folder, sub),
                 dst=os.path.join(dst_bin, sub))
        copy(self, "*.gr", src=os.path.join(self.source_folder, "data"),
             dst=os.path.join(dst_bin, "data"))
        for lic in glob.glob(os.path.join(self.source_folder, "license.txt")) + \
                   glob.glob(os.path.join(self.source_folder, "LICENSE*")) + \
                   glob.glob(os.path.join(self.source_folder, "COPYING*")):
            copy(self, os.path.basename(lic), src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
