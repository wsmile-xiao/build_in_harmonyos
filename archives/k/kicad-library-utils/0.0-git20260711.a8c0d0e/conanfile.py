#!/usr/bin/env python3
"""Conan recipe for kicad-library-utils 0.0-git20260711.a8c0d0e — KiCad 官方库检查工具集。

上游事实（冻结 commit a8c0d0ec，归档 562 个条目）：
  * 上游仓库 https://gitlab.com/kicad/libraries/kicad-library-utils 为无 tag 的
    滚动仓库，本包版本 0.0-git<date>.<short-sha> 由冻结 commit 唯一确定；
  * 纯 Python 工具集：无任何 C/C++ 编译单元、无 CMake/Autotools、非 pip 包
    （pyproject.toml 仅含样式工具配置）；上游没有 install() 语义；
  * 入口脚本（klc-check/check_symbol.py 等）以
    ``os.path.join(os.path.dirname(__file__), os.pardir, "common")`` 相对引用
    公共模块 —— 安装必须整体保留源码树布局，不能把脚本拆散到 bin/。

因此本配方没有构建步骤：source() 下载归档后，package() 把整棵源码树原样复制到
``share/kicad-library-utils/``，并把各工具子目录声明为 bindirs 供消费者注入 PATH。
脚本统一以 ``python3 -B`` 方式调用（见 test_package），不依赖可执行位。

依赖闭包：核心检查路径（common/ + klc-check/）仅依赖 Python 标准库，配方不声明
任何 Conan 依赖；bs4/click/requests/PIL 等可选重依赖只被 tools/、symbol-generators/、
html-diff/、scripts/ 子目录按需引用。

类型判定：本包是真实的命令行工具集合（KiCad 官方库 CI 的门禁程序），按 R38 以
``package_type = "application"`` + 软件级 commands.json 声明，而非资源型 unknown。
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get

required_conan_version = ">=2.0.0"


class KicadLibraryUtilsConan(ConanFile):
    name = "kicad-library-utils"
    version = "0.0-git20260711.a8c0d0e"
    description = ("Official KiCad library maintenance tools: KLC rule checkers for "
                   "symbols/footprints/lib-tables, library comparison and symbol "
                   "generation (pure Python CLI tool suite)")
    homepage = "https://gitlab.com/kicad/libraries/kicad-library-utils"
    license = "GPL-3.0"
    url = ""
    topics = ("kicad", "eda", "klc", "quality-check", "tools")

    # 命令行工具集合（R38）：真实 CLI 工具，软件级 commands.json 已声明
    package_type = "application"
    # L0p：OHOS profile 需要 os/compiler/build_type/arch 四项齐备
    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "conandata.yml"

    def source(self):
        # 归档根目录为 kicad-library-utils-<sha>-<sha>/，必须 strip_root
        get(self, **self.conan_data["sources"],
            destination=self.source_folder, strip_root=True)

    def build(self):
        # 纯 Python 工具集：上游无任何构建步骤（无编译器调用、无构建系统），
        # 显式 no-op 以说明这是刻意设计而非遗漏。
        pass

    def package(self):
        # 安装语义 = 整体保留上游源码树布局：脚本以相对路径引用 ../common，
        # 拆散安装会破坏 import。含上游测试数据（klc-check/test_symbol/、
        # klc-check/test_footprint.pretty/），供消费者复跑上游测试。
        copy(self, "*", self.source_folder,
             os.path.join(self.package_folder, "share", "kicad-library-utils"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
        # 可执行脚本所在子目录（相对包根），供消费者环境注入 PATH；
        # 脚本统一用 python3 -B 调用，不依赖可执行位
        utils_root = os.path.join("share", "kicad-library-utils")
        self.cpp_info.bindirs = [
            os.path.join(utils_root, "klc-check"),
            os.path.join(utils_root, "tools"),
            os.path.join(utils_root, "symbol-generators"),
            os.path.join(utils_root, "html-diff"),
            os.path.join(utils_root, "scripts"),
        ]
        self.cpp_info.set_property("cmake_file_name", "kicad-library-utils")
