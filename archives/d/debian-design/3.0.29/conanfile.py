#!/usr/bin/env python3
"""Conan recipe for debian-design 3.0.29 — Debian blend 节点数据包（纯数据）。

上游: https://tracker.debian.org/pkg/debian-design （Debian 原生包）
源码分发: https://deb.debian.org/debian/pool/main/d/debian-design/debian-design_3.0.29.tar.xz
（本配方走清华 TUNA 镜像同一份文件，sha256 与 .dsc 的 Checksums-Sha256 一致）

Debian Design 的交付形态与其他 Pure Blend 不同：它没有 `tasks/`，而是

    nodes/*.yml                 4 个「节点」，每个节点给出一份**类清单**（classes）
    skel/preseed.cfg.in         debian-installer 预置模板（Template Toolkit 语法）
    skel/script.sh.in           安装/更新脚本模板

上游 `Makefile` 用外部的 `boxer compose --nodedir nodes --skeldir skel --suite <suite> <node>`
把「节点 + 模板」组合成 consumer（debian-live / live-build / debian-installer）真正读取的
`content/<node>/preseed.cfg` 与 `content/<node>/script.sh`，再生成 `content/MD5SUMS`、
`content/SHA*SUMS`。本包交付**组合所需的全部输入**（nodes/ + skel/ + Makefile + NEWS/TODO）：

    share/design-blends/nodes/<node>.yml        节点类清单
    share/design-blends/skel/preseed.cfg.in     d-i 预置模板
    share/design-blends/skel/script.sh.in       安装脚本模板
    share/design-blends/Makefile                上游组合/校验骨架
    share/doc/debian-design/{NEWS,TODO}
    licenses/copyright

**纯数据包，无编译步骤**：`build()` 只做本体自检（节点与模板必须齐全、每个节点至少一条类），
组合与校验由消费者用例 `test_package/consumer_design.py` 按真实流程执行。

License: 见 debian/copyright
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, export_conandata_patches, apply_conandata_patches, get
from conan.tools.layout import basic_layout


class DesignBlendConan(ConanFile):
    name = "debian-design"
    version = "3.0.29"
    description = "Debian Design blend node data — live installer preseed/script templates"
    license = "GPL-2.0-or-later"
    homepage = "https://tracker.debian.org/pkg/debian-design"
    url = "https://tracker.debian.org/pkg/debian-design"
    package_type = "unknown"          # 纯数据包：不含编译器产物

    _sharedir = os.path.join("share", "design-blends")
    _skel_files = ("preseed.cfg.in", "script.sh.in")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # 没有编译器参与；这里只做本体自检：节点与两份模板必须都在，
        # 且每个节点至少列出一条 class —— 否则交付的是残包。
        nodes_dir = os.path.join(self.source_folder, "nodes")
        skel_dir = os.path.join(self.source_folder, "skel")
        if not os.path.isdir(nodes_dir):
            raise ConanException("upstream nodes/ directory missing")
        if not os.path.isdir(skel_dir):
            raise ConanException("upstream skel/ directory missing")
        nodes = sorted(n for n in os.listdir(nodes_dir) if n.endswith(".yml"))
        if not nodes:
            raise ConanException("upstream nodes/ contains no *.yml")
        for name in self._skel_files:
            if not os.path.isfile(os.path.join(skel_dir, name)):
                raise ConanException(f"upstream skel/{name} missing")
        classes = 0
        for node in nodes:
            with open(os.path.join(nodes_dir, node), encoding="utf-8",
                      errors="replace") as handle:
                text = handle.read()
            in_classes = False
            count = 0
            for line in text.splitlines():
                if line.strip().startswith("classes:"):
                    in_classes = True
                    continue
                if in_classes:
                    if line.startswith("  - ") or line.startswith("- "):
                        count += 1
                    elif line.strip() and not line.startswith(" "):
                        in_classes = False
            if count == 0:
                raise ConanException(f"node {node} lists no class")
            classes += count
        self.output.info(f"{self.name}: {len(nodes)} nodes, {classes} classes, "
                         f"{len(self._skel_files)} skel templates")

    def package(self):
        # copy() 复制 src 的**内容**：src 直接指向被复制的目录本身
        copy(self, "*", src=os.path.join(self.source_folder, "nodes"),
             dst=os.path.join(self.package_folder, self._sharedir, "nodes"))
        copy(self, "*", src=os.path.join(self.source_folder, "skel"),
             dst=os.path.join(self.package_folder, self._sharedir, "skel"))
        for name in ("Makefile", "NEWS", "TODO", "README"):
            copy(self, name, src=self.source_folder,
                 dst=os.path.join(self.package_folder, self._sharedir))
            copy(self, name, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "share", "doc", self.name))
        copy(self, "copyright", src=os.path.join(self.source_folder, "debian"),
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 纯数据包：清空默认的 include/lib/bin 目录，只暴露资源目录契约
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = [self._sharedir]
        share = os.path.join(self.package_folder, self._sharedir)
        self.buildenv_info.define("DESIGN_BLEND_DIR", share)
        self.runenv_info.define("DESIGN_BLEND_DIR", share)
        self.output.info(f"DESIGN_BLEND_DIR={share}")
