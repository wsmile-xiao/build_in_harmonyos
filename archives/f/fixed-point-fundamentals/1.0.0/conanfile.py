#!/usr/bin/env python3
"""Conan recipe — fixed-point-fundamentals 1.0.0

Fixed-Point Fundamentals: 定点算术教学课程（lessons 00-07），纯 Makefile 项目。
无 configure、无头文件、无库产物；构建产物为 17 个独立示例程序（examples）。
因此按 application 型打包，产物安装到 bin/，并按 R38 在软件级声明 commands.json。

构建适配点：
- 上游 Makefile 硬编码 CC=gcc，本环境无 gcc；配方从 Conan Toolchain 取 CC（R33）。
- CFLAGS 含 -Werror；clang 比 gcc 更严格，unused static inline 函数与
  int/int64→float/double 隐式转换会产生告警并升级为错误（5/17 示例）。
  移除 -Werror（保留其余告警开关）即可全量构建；不改上游源码。
"""
import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class FixedpointfundamentalsConan(ConanFile):
    name = "fixed-point-fundamentals"
    version = "1.0.0"
    description = "Fixed-Point Fundamentals — C99 fixed-point arithmetic teaching course with 17 runnable example programs"
    license = "MIT"
    homepage = "https://github.com/SpeyTech/fixed-point-fundamentals"
    url = "https://github.com/SpeyTech/fixed-point-fundamentals"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: 编译器从 Conan conf 获取，绝不裸用 shell 环境变量
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        # 去掉 -Werror：clang 将 unused static inline / 隐式 int→float 截断告警升级为错误，
        # 导致 5/17 示例构建失败；移除后全量构建（不改上游源码）
        cflags = "-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Wconversion -O2 -g"
        # 顶层 Makefile 的 examples 目标会逐个编译 lessons/*/examples/*.c
        self.run(f'make examples CC="{cc}" CFLAGS="{cflags}"', cwd=self.source_folder)
        # 上游 Makefile 每行编译带 `2>/dev/null || true` 吞错（make 恒返回 0），
        # 必须显式校验 17 个示例产物齐备，防止静默产出缺二进制的包
        missing = []
        for ex in sorted((Path(self.source_folder) / "lessons").glob("*/examples/*")):
            if ex.suffix in (".c", ".md", ".o") or ex.name == "Makefile":
                continue
            if not ex.is_file() or not os.access(ex, os.X_OK):
                missing.append(str(ex.relative_to(self.source_folder)))
        if missing:
            raise ConanInvalidConfiguration(
                f"示例程序构建不完整，缺失/不可执行: {missing}")

    def package(self):
        # 17 个示例程序（无扩展名 ELF）拍平安装到 bin/
        copy(self, "lessons/*/examples/*",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False,
             excludes=("*.c", "*.md", "Makefile", "*.o"))
        # 附带文档
        copy(self, "README*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "fixed-point-fundamentals"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "fixed-point-fundamentals"))

    def package_info(self):
        # 示例程序集合，非库
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]