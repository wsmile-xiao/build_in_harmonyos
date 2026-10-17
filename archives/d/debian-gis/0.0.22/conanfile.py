#!/usr/bin/env python3
"""Conan recipe for debian-gis 0.0.22 — Debian Pure Blend 任务数据包（纯数据）。

上游: https://tracker.debian.org/pkg/debian-gis （Debian 原生包）
源码分发: https://deb.debian.org/debian/pool/main/d/debian-gis/debian-gis_0.0.22.tar.xz
（本配方走清华 TUNA 镜像同一份文件，sha256 与 .dsc 的 Checksums-Sha256 一致）

Debian Pure Blend 的"任务"机制：`tasks/<name>` 是每个任务包的**源描述**
（`Task:` / `Description:` / `Depends:` / `Recommends:`），`blends-dev` 把它们
合并、展开成 `<blend>-tasks.desc`（tasksel 消费的最终形态）。

本包交付两份形态，让消费方既能直接用成品、也能拿到逐任务的源：

    share/tasksel/descs/debian-gis-tasks.desc   生成好的任务描述（tasksel 形态）
    share/blends/debian-gis/tasks/<name>        逐任务源描述
    share/pixmaps/debian-gis-logo.svg           Blend logo（如有）
    share/doc/debian-gis/AUTHORS
    licenses/copyright 或 COPYING

**纯数据包，无编译步骤**：上游 `Makefile` 需要 `blends-dev`（`/usr/share/blends-dev/Makefile`）
才能重新生成 `.desc`，但**生成结果已经随源包发布**，本包直接交付它；
`src/`（若干 Python 维护脚本）与 `dependency_data/`（依赖快照）不安装。

License: GPL-2.0-or-later（见 COPYING / debian/copyright）
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, export_conandata_patches, apply_conandata_patches, get
from conan.tools.layout import basic_layout


class BlendDebianGisConan(ConanFile):
    name = "debian-gis"
    version = "0.0.22"
    description = "Debian Pure Blend task data — debian-gis"
    license = "GPL-2.0-or-later"
    homepage = "https://tracker.debian.org/pkg/debian-gis"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 纯数据包：无编译、无 settings，产物与架构无关。
    package_type = "unknown"

    no_copy_source = True

    _desc_name = "debian-gis-tasks.desc"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # 没有编译器参与；这里只做本体自检：生成好的 .desc 与逐任务源必须都在，
        # 并且 .desc 里的每个任务都能找到对应的源文件 —— 否则交付的是残包。
        desc_path = os.path.join(self.source_folder, self._desc_name)
        tasks_dir = os.path.join(self.source_folder, "tasks")
        if not os.path.isfile(desc_path):
            raise ConanException(f"{self._desc_name} missing from upstream")
        if not os.path.isdir(tasks_dir):
            raise ConanException("upstream tasks/ directory missing")

        with open(desc_path, encoding="utf-8", errors="replace") as handle:
            desc = handle.read()
        names = [line.split(":", 1)[1].strip() for line in desc.splitlines()
                 if line.startswith("Task:")]
        if not names:
            raise ConanException(f"{self._desc_name} contains no Task: sections")

        sources = set(os.listdir(tasks_dir))
        prefix = "gis-"
        missing = [n for n in names
                   if n != self.name and n.startswith(prefix)
                   and n[len(prefix):] not in sources]
        if missing:
            raise ConanException(
                f"tasks referenced by {self._desc_name} have no source file: {missing}")
        self.output.info(f"{self.name}: {len(names)} tasks, {len(sources)} task sources")

    def package(self):
        # copy() 复制 src 的**内容**：src 必须直接指向 tasks/ 本身
        copy(self, "*", src=os.path.join(self.source_folder, "tasks"),
             dst=os.path.join(self.package_folder, "share", "blends", self.name, "tasks"))
        copy(self, self._desc_name, src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "tasksel", "descs"))
        copy(self, "*-logo.svg", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "pixmaps"))
        copy(self, "AUTHORS", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", self.name))
        for name in ("COPYING",):
            copy(self, name, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "copyright", src=os.path.join(self.source_folder, "debian"),
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = [os.path.join("share", "blends", self.name)]
        share = os.path.join(self.package_folder, "share")
        self.buildenv_info.define("BLEND_TASKS_DESC_DIR",
                                  os.path.join(share, "tasksel", "descs"))
        self.runenv_info.define("BLEND_TASKS_DESC_DIR",
                                os.path.join(share, "tasksel", "descs"))
        self.output.info(f"BLEND_TASKS_DESC_DIR={os.path.join(share, 'tasksel', 'descs')}")
