#!/usr/bin/env python3
"""Conan recipe — zsdx 1.12.3（The Legend of Zelda - Mystery of Solarus DX 游戏数据包）。

zsdx 是 Solarus 2D 引擎的 quest 数据包：data/ 下 1143 个文件（293 个 Lua 游戏
脚本 + 地图/贴图/音效/字体等资源），零编译单元——上游 CMakeLists.txt 第 3 行
`project(ZSDX NONE)`。上游"构建"的唯一产物是把 data/ 打成 data.solarus zip：
根目录 make_zip 脚本原文 `cd data && zip -r ../../data.solarus *`。

关键契约：zip 条目必须以 data/ 内容为根（main.lua/quest.dat 等在 zip 根），
Solarus 引擎按根级路径加载 quest，带顶层前缀目录会直接损坏。

OHOS 适配要点：
- 纯数据包：不声明对 Solarus 引擎的 conan 依赖（官方仓无 solarus recipe；引擎
  只影响"实跑游戏"，不影响数据包的构建/交付），无编译器/cmake tool_requires。
- build() 用 python 标准库 zipfile 复刻 make_zip 语义：os.walk 显式收集全部
  文件（含点文件，ieee-data copy("*") 丢 .lastupdate 教训；zsdx data/ 实测无
  点文件），arcname 统一 POSIX 斜杠。不依赖设备 zip 命令的存在性/版本。
- 安装布局对齐上游 CMake install 语义：data.solarus → share/solarus/zsdx/
  （SOLARUS_INSTALL_DATADIR 默认 share/solarus + quest_name zsdx）。
- license.txt（复合许可声明：Lua 脚本 GPL-3.0 + 自创数据 CC-BY-SA-4.0 +
  Nintendo 版权内容 fair-use 声明）→ licenses/。
- 上游测试：.gitlab-ci.yml 仅 2 行 include solarus-devops 的 quests.yml（引擎级
  运行时测试：预编译 Solarus linux 工件 + Xvfb 逐地图跑），zsdx 自身无 tests/
  目录、data/maps 下无 test_* 地图——NO_UPSTREAM_TESTS，详见 notes.md。
"""

import os
import zipfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class ZsdxConan(ConanFile):
    name = "zsdx"
    version = "1.12.3"
    description = ("The Legend of Zelda - Mystery of Solarus DX — "
                   "quest data package for the Solarus 2D game engine")
    license = "GPL-3.0-only AND CC-BY-SA-4.0"
    homepage = "https://gitlab.com/solarus-games/games/zsdx"
    url = ""  # CI fills this
    topics = ("solarus", "quest", "game-data", "zelda")

    # 纯数据包，无 bin/lib 产物。header-library 在本仓是"非可执行/非库"数据包
    # 的惯用表达（lomiri-schemas 先例）；application 会误触发 R38 commands.json
    # 要求（L0k），而 zsdx 没有任何命令行工具。
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        """复刻上游 make_zip：`cd data && zip -r ../../data.solarus *`。

        产出 <build>/data.solarus，条目相对 data/ 为根。
        """
        data_dir = os.path.join(self.source_folder, "data")
        if not os.path.isdir(data_dir):
            raise ConanException(f"source data/ directory missing: {data_dir}")
        out_path = os.path.join(self.build_folder, "data.solarus")
        entries = 0
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(data_dir):
                dirs.sort()
                for fname in sorted(files):
                    full = os.path.join(root, fname)
                    arcname = os.path.relpath(full, data_dir).replace("\\", "/")
                    zf.write(full, arcname)
                    entries += 1
        if entries == 0:
            raise ConanException(f"no files packaged from {data_dir}")
        self.output.info(
            f"data.solarus: {entries} entries, {os.path.getsize(out_path)} bytes")

    def package(self):
        # 上游 install(FILES data.solarus DESTINATION share/solarus/zsdx)
        quest_dir = os.path.join(self.package_folder, "share", "solarus", "zsdx")
        copy(self, "data.solarus", src=self.build_folder, dst=quest_dir,
             keep_path=False)
        copy(self, "license.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # 纯数据包：无库/头文件/可执行文件；quest 数据经 resdirs 暴露
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share/solarus/zsdx"]
        self.buildenv_info.define_path(
            "ZSDX_QUEST_DIR",
            os.path.join(self.package_folder, "share", "solarus", "zsdx"))
