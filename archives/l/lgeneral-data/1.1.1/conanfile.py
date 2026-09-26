#!/usr/bin/env python3
"""Conan recipe for lgeneral-data 1.1.1 — LGeneral 游戏内容包（k.u.k General 战役）。

上游: https://tracker.debian.org/pkg/lgeneral-data （Debian 源码包即上游分发形态）
源码分发: https://deb.debian.org/debian/pool/main/l/lgeneral-data/lgeneral-data_1.1.1.orig.tar.gz
（本配方走清华 TUNA 镜像同一份文件，sha256 与 Debian .dsc 的 Checksums-Sha256 一致）

这是一个**纯数据包**：没有任何编译步骤。交付 LGeneral（开源一战题材回合制战略游戏）
的免费内容包 "k.u.k General"，按上游 README 的约定安装到 LGeneral 的数据目录：

    share/games/lgeneral/campaigns/           战役定义（kukgen）
    share/games/lgeneral/gfx/                 旗帜 / 单位 / 地形贴图（59 个 BMP）
    share/games/lgeneral/maps/                地图（maps/kukgen/ 61 个 + kukgen.tdb）
    share/games/lgeneral/nations/             国家表（kukgen.ndb）
    share/games/lgeneral/scenarios/           剧本（scenarios/kukgen/ 22 个 + .order）
    share/games/lgeneral/sounds/              音效（8 个 WAV + LICENSE.sounds）
    share/games/lgeneral/units/               单位表（kukgen.udb）
    share/games/lgeneral/scenlist             剧本清单（22 行条目）

上游 README 明确写了安装方式："Copy the directories campaigns, gfx, maps, nations,
scenarios, sounds and units to your LGeneral data directory (e.g.
/usr/share/games/lgeneral)" —— 本配方按这句执行，只把 `/usr/share` 换成 Conan 的
`share/`。

License: CC-BY-SA-3.0
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, export_conandata_patches, apply_conandata_patches, get
from conan.tools.layout import basic_layout


class LgeneralDataConan(ConanFile):
    name = "lgeneral-data"
    version = "1.1.1"
    description = ("LGeneral content pack — the k.u.k General campaign "
                   "(units, nations, terrain sprites, maps, scenarios, sounds)")
    license = "CC-BY-SA-3.0"
    homepage = "https://tracker.debian.org/pkg/lgeneral-data"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 纯数据包：无编译、无 settings，产物与架构无关。
    package_type = "unknown"

    no_copy_source = True

    _data_subdir = os.path.join("share", "games", "lgeneral")

    # 上游 README 点名的 7 个数据目录（缺一不可），另有清单文件 scenlist
    _DATA_DIRS = ("campaigns", "gfx", "maps", "nations",
                  "scenarios", "sounds", "units")
    _DATA_FILES = ("scenlist",)

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
        missing = [name for name in self._DATA_DIRS
                   if not os.path.isdir(os.path.join(self.source_folder, name))]
        missing += [name for name in self._DATA_FILES
                    if not os.path.isfile(os.path.join(self.source_folder, name))]
        if missing:
            raise ConanException(f"upstream data tree is incomplete: {missing}")

        # 剧本清单必须与 scenarios/kukgen/ 对得上（22 条），否则内容包是残的
        scen_dir = os.path.join(self.source_folder, "scenarios", "kukgen")
        scenarios = [f for f in os.listdir(scen_dir) if not f.startswith(".")]
        with open(os.path.join(self.source_folder, "scenlist"),
                  encoding="utf-8", errors="replace") as handle:
            listed = [line.strip().rstrip("*").strip() for line in handle
                      if line.strip()
                      and not line.startswith("Scenarios")
                      and not line.startswith("*")]
        absent = [name for name in listed if name not in scenarios]
        if absent:
            raise ConanException(
                f"scenlist references scenarios that are not in the tree: {absent}")
        self.output.info(f"lgeneral-data: {len(listed)} scenarios, "
                         f"{len(scenarios)} scenario files")

    def package(self):
        data_dir = os.path.join(self.package_folder, self._data_subdir)

        for name in self._DATA_DIRS:
            # 目标目录必须带上自身目录名：copy() 复制的是 src 的**内容**，
            # 直接写 dst=data_dir 会把 maps/kukgen 铺成 lgeneral/kukgen。
            copy(self, "*", src=os.path.join(self.source_folder, name),
                 dst=os.path.join(data_dir, name))

        for name in self._DATA_FILES:
            copy(self, name, src=self.source_folder, dst=data_dir)

        copy(self, "*", src=os.path.join(self.source_folder, "docs"),
             dst=os.path.join(self.package_folder, "share", "doc", "lgeneral-data"))

        # 三份许可证分处不同目录（COPYING 是 GPL 工具链文本，LICENSE 是内容包
        # 的 CC-BY-SA 声明，sounds/LICENSE.sounds 是音效单独声明），逐份收集。
        lic_dir = os.path.join(self.package_folder, "licenses")
        for name in ("COPYING", "LICENSE"):
            copy(self, name, src=self.source_folder, dst=lic_dir)
        copy(self, "LICENSE.sounds",
             src=os.path.join(self.source_folder, "sounds"), dst=lic_dir)

    def package_info(self):
        # 纯数据包：没有库、没有可执行文件、没有头文件。
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

        self.cpp_info.resdirs = [self._data_subdir]

        data_dir = os.path.join(self.package_folder, self._data_subdir)
        self.buildenv_info.define("LGENERAL_DATA_DIR", data_dir)
        self.runenv_info.define("LGENERAL_DATA_DIR", data_dir)
        self.output.info(f"LGENERAL_DATA_DIR={data_dir}")
