#!/usr/bin/env python3
"""Conan test_package — nsnake 3.0.1.1.

两件事分开做，避免"结构检查冒充测试"：
1. 真实执行被测包的二进制（R34）：`nsnake --version` 必须跑通并校验输出内容；
2. 打包完整性回归断言（3.0.1.1 的新增目标）：上游 `make install` 会安装的
   关卡 / man6 / 图标 / pixmaps / desktop 必须全部在包内且非空、占位符已替换。
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException

LEVEL_COUNT = 31
DATA_FILES = [
    "share/man/man6/nsnake.6",
    "share/pixmaps/nsnake.xpm",
    "share/applications/nsnake.desktop",
    "share/icons/hicolor/16x16/apps/nsnake.png",
    "share/icons/hicolor/32x32/apps/nsnake.png",
]


class NsnakeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # HarmonyOS PC platform consumer test: reject a non-OHOS/non-arm64 run.
        if str(self.settings.os) != "OHOS":
            raise ConanException(f"expected OHOS test host, got {self.settings.os}")
        if str(self.settings.arch) != "armv8":
            raise ConanException(f"expected OHOS arm64 test host, got {self.settings.arch}")
        self.output.info("HarmonyOS PC aarch64 platform test: PASS")

        pkg = self.dependencies["nsnake"].package_folder
        bin_path = os.path.join(pkg, "bin", "nsnake")

        # ── 1. 真实执行被测包 ──
        self.output.info(f"Running binary: {bin_path}")
        self.run(f"{bin_path} --version", env="conanrun")
        # shell=True（Conan 2 的 self.run 默认），管道退出码即断言结果
        self.run(f"{bin_path} --version | grep -q 'nsnake v'", env="conanrun")
        # 构建日期必须固定（配方向 make 传 DATE=Jul2014），否则产物不可复现
        self.run(f"{bin_path} --version | grep -q 'Jul2014'", env="conanrun")

        # ── 2. 打包完整性回归断言 ──
        if not os.path.isfile(bin_path):
            raise ConanException("缺 bin/nsnake")
        for rel in DATA_FILES:
            full = os.path.join(pkg, rel.replace("/", os.sep))
            if not os.path.isfile(full):
                raise ConanException(f"缺数据文件: {rel}")
            if os.path.getsize(full) == 0:
                raise ConanException(f"数据文件为空: {rel}")

        level_dir = os.path.join(pkg, "share", "games", "nsnake", "levels")
        levels = [f for f in os.listdir(level_dir) if f.endswith(".nsnake")] \
            if os.path.isdir(level_dir) else []
        if len(levels) != LEVEL_COUNT:
            raise ConanException(
                f"关卡数不符: 期望 {LEVEL_COUNT}，实际 {len(levels)}")

        man = os.path.join(pkg, "share", "man", "man6", "nsnake.6")
        with open(man, encoding="utf-8", errors="replace") as handle:
            man_text = handle.read()
        if re.search(r"\b(VERSION|DATE)\b", man_text):
            raise ConanException("man6 仍含未替换占位符")
        if ".TH nsnake 6" not in man_text:
            raise ConanException("man6 内容非 nsnake 手册")

        self.output.info(
            f"OK: binary executed, {len(levels)} levels + {len(DATA_FILES)} "
            "data files verified")
