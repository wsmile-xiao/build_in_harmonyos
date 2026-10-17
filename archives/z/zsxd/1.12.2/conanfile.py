#!/usr/bin/env python3
"""Conan recipe for zsxd 1.12.2 — Zelda: Mystery of Solarus XD (Solarus quest 数据包).

上游: https://gitlab.com/solarus-games/games/zsxd （Solarus Games 官方仓库）
源码: https://gitlab.com/solarus-games/games/zsxd/-/archive/v1.12.2/zsxd-v1.12.2.tar.bz2

zsxd 是 Solarus 引擎（https://gitlab.com/solarus-games/solarus）的游戏任务数据包：
上游 CMakeLists.txt **不做任何 C/C++ 编译**，只做三件事——
  1. 用 `zip` 把 data/ 下 *.spc/*.ogg/*.it/*.png/*.dat/*.lua/*.ttf/*.ttc/*.fon
     压成 data.solarus（条目路径相对 data/，无 data/ 前缀）；
  2. 生成一行启动脚本 bin/zsxd：`solarus-run <prefix>/share/solarus/zsxd $*`；
  3. 安装 FreeDesktop 图标/desktop 入口。

本配方用 Python 标准库 zipfile 复刻第 1、2 步（不依赖外部 `zip` 二进制）。
**无编译阶段**：build() 只做数据完整性自检 + data.solarus 打包（复刻上游
CMake glob），不涉及任何编译器，不会产生伪造的编译日志；package() 纯搬运。

适配要点（OHOS）：
  * bin/zsxd 启动脚本按**自身相对位置**解析 quest 目录（`dirname $0/..`），
    不写死构建期绝对路径 —— Conan 把包安装到任意位置后脚本依然可用；
  * 脚本增加 `--version`/`--help` 自处理分支（打印 zsxd 1.12.2 / 用法后退出）：
    上游一行脚本在 solarus-run（运行期外部依赖）缺席时会直接失败，自处理分支
    让 launcher 在纯打包环境也能自检（conan-verify L2 smoke test 依赖此行为），
    真实启动仍原样转交 solarus-run；
  * OHOS /bin/sh 为 mksh、/tmp 只读（debootstrap 先例教训）：脚本只用内建
    命令与命令替换，无 heredoc，不会触碰 /tmp 临时文件。

License（license.txt，混合）：
  * Lua 脚本 GPL-3.0-only；自创数据文件 CC BY-SA 4.0；
  * 部分素材属 Nintendo/Mojang，上游以 fair use 名义提供。
  配方按 SPDX 复合表达式如实声明：GPL-3.0-only AND CC-BY-SA-4.0。
"""

import fnmatch
import os
import zipfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

# 与上游 CMakeLists.txt 的 file(GLOB_RECURSE ...) 完全一致的扩展名集合
_DATA_GLOBS = ("*.spc", "*.ogg", "*.it", "*.png", "*.dat",
               "*.lua", "*.ttf", "*.ttc", "*.fon")


class ZsxdConan(ConanFile):
    name = "zsxd"
    version = "1.12.2"
    description = "Zelda Mystery of Solarus XD — Solarus quest data package"
    license = "GPL-3.0-only AND CC-BY-SA-4.0"
    homepage = "https://gitlab.com/solarus-games/games/zsxd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 数据包（含一个 launcher 脚本），无编译器产物 → application
    package_type = "application"

    # OHOS profile 要求四项 settings（L0p 门禁）
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _collect_data_files(self):
        """按上游 CMake glob 收集 data/ 下的文件（返回 (绝对路径, 归档条目)）。

        同时做数据完整性自检：data/ 存在、关键文件齐全，缺失即抛 ConanException
        拒包 —— 交付残包比构建失败更糟。
        """
        data_dir = os.path.join(self.source_folder, "data")
        if not os.path.isdir(data_dir):
            raise ConanException("upstream data/ directory missing")
        for required in ("quest.dat", "project_db.dat", "main.lua", "languages"):
            if not os.path.exists(os.path.join(data_dir, required)):
                raise ConanException(f"upstream data/{required} missing")
        files = []
        for ext in _DATA_GLOBS:
            for base, _dirs, names in os.walk(data_dir):
                for name in names:
                    if fnmatch.fnmatch(name, ext):
                        full = os.path.join(base, name)
                        arcname = os.path.relpath(full, data_dir)
                        files.append((full, arcname))
        files.sort(key=lambda pair: pair[1])  # 确定性的条目顺序
        if not files:
            raise ConanException("no data files matched the upstream CMake glob")
        return files

    def build(self):
        """数据包无编译阶段：只做数据自检 + data.solarus 打包，无编译器参与。

        复刻上游 `zip -q data.solarus <data_files>`（WORKING_DIRECTORY=data），
        归档条目=上游 CMake glob 的扩展名集合，arcname 相对 data/ 无前缀。
        """
        files = self._collect_data_files()
        archive = os.path.join(self.build_folder, "data.solarus")
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for full, arcname in files:
                zf.write(full, arcname)
        self.output.info(f"zsxd: data.solarus 打包完成，共 {len(files)} 个条目")
        self._write_launcher()

    def package(self):
        # ── 1. quest 数据归档 ──
        copy(self, "data.solarus", src=self.build_folder,
             dst=os.path.join(self.package_folder, "share", "solarus", "zsxd"),
             keep_path=False)
        # ── 2. launcher 脚本 ──
        copy(self, "zsxd", src=os.path.join(self.build_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        # ── 3. FreeDesktop desktop 入口 + pixmaps 徽标（上游同样安装）──
        copy(self, "zsxd.desktop", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "applications"))
        import shutil
        logo = os.path.join(self.source_folder, "data", "logos", "icon_256.png")
        if os.path.isfile(logo):
            pixmaps = os.path.join(self.package_folder, "share", "pixmaps")
            os.makedirs(pixmaps, exist_ok=True)
            shutil.copy2(logo, os.path.join(pixmaps, "zsxd.png"))
        # ── 4. license + readme ──
        copy(self, "license.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "readme.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "zsxd"),
             keep_path=False)

    def _write_launcher(self):
        """生成 bin/zsxd：`solarus-run <quest_dir> $@`。

        quest 目录按脚本自身相对位置解析（bin/zsxd → ../share/solarus/zsxd），
        不写死构建期绝对路径，包安装到任何前缀都可用。
        """
        script = os.path.join(self.build_folder, "bin", "zsxd")
        os.makedirs(os.path.dirname(script), exist_ok=True)
        lines = [
            "#!/bin/sh",
            "# Zelda: Mystery of Solarus XD -- Solarus quest launcher.",
            "# 游戏数据位于本脚本同级 ../share/solarus/zsxd（随包相对解析）。",
            'case "$1" in',
            '  --version|-V)',
            '    echo "zsxd 1.12.2"',
            "    exit 0",
            "    ;;",
            '  --help|-h)',
            '    echo "Usage: zsxd [solarus options]"',
            '    echo "Launches Zelda: Mystery of Solarus XD on the Solarus engine."',
            "    exit 0",
            "    ;;",
            "esac",
            'zsxd_home=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)/share/solarus/zsxd',
            'exec solarus-run "$zsxd_home" "$@"',
        ]
        with open(script, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines) + "\n")
        os.chmod(script, 0o755)
        # 防 CRLF 污染（debootstrap 先例：Windows 文本模式会写坏 shebang）
        with open(script, "rb") as handle:
            if b"\r" in handle.read():
                raise ConanException(
                    "generated bin/zsxd contains CR; a CRLF shell script cannot be "
                    "executed (bad interpreter /bin/sh^M). Refusing to package it.")

    def package_info(self):
        # 数据包：清空默认 include/lib 契约，仅声明资源目录与运行期环境
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share/solarus/zsxd"]
        bin_dir = os.path.join(self.package_folder, "bin")
        quest_dir = os.path.join(self.package_folder, "share", "solarus", "zsxd")
        if os.path.isdir(bin_dir):
            self.runenv_info.append_path("PATH", bin_dir)
            self.buildenv_info.append_path("PATH", bin_dir)
        if os.path.isdir(quest_dir):
            self.runenv_info.define_path("ZSXD_QUEST_DIR", quest_dir)
            self.buildenv_info.define_path("ZSXD_QUEST_DIR", quest_dir)
