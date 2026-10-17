#!/usr/bin/env python3
"""Conan recipe for kicad-symbols 10.0.4 — KiCad 官方原理图符号库（数据/资源型包）。

上游事实（已在 PR 中逐条给出证据）：
  * 上游仓库 https://gitlab.com/kicad/libraries/kicad-symbols，tag 10.0.4；
  * 仓库内容为 223 个 ``*.kicad_symdir`` 符号库目录（KiCad 10 的“每符号一文件”
    目录格式，共 23012 个文件）+ ``sym-lib-table`` + ``Simulation_SPICE.sp``；
  * 上游唯一的构建逻辑是顶层 ``CMakeLists.txt``：``project(kicad-symbols NONE)``
    —— **没有任何 C/C++ 编译单元**；它用 ``tools/kicad_lib_pack.py``（Python）把
    ``*.kicad_symdir/`` 打包成单文件 ``<lib>.kicad_sym``（``KICAD_PACK_SYM_LIBRARIES``，
    上游默认 ON），再把库表改写为指向 ``.kicad_sym``，随后 ``install()`` 到
    ``share/kicad/symbols`` 与 ``share/kicad/template``。

本配方刻意**使用上游构建系统（CMake）**而不是自己 copy 文件：上游 install() 规则
已经完整表达了“打包 + 安装 + 库表改写”的语义，复用它可以保证产物与上游/发行版一致，
并且让上游的打包脚本（kicad_lib_pack.py）成为被真实执行的代码路径。

产物布局与 Debian 官方包 ``kicad-symbols``（10.0.6-1, all）实测一致：
    share/kicad/symbols/<lib>.kicad_sym        （223 个打包库 + Simulation_SPICE.sp）
    share/kicad/template/sym-lib-table         （改写为 .kicad_sym 的全局库表）
    licenses/LICENSE.md

平台说明：本包不含可执行文件与 C/C++ 产物，因此 package_type 取 unknown 而非
application（后者会被 R38/commands.json 门禁判定为命令行工具包），按资源型数据包处理
（知识库 E255 / E305 同类模式）。
"""
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get

required_conan_version = ">=2.0.0"


class KicadSymbolsConan(ConanFile):
    name = "kicad-symbols"
    version = "10.0.4"
    description = ("Official KiCad symbol libraries (schematic symbol data for ~30k "
                   "components across 223 libraries); data/resource package with no "
                   "C/C++ library artifact")
    homepage = "https://gitlab.com/kicad/libraries/kicad-symbols"
    license = "CC-BY-SA-4.0"
    url = ""
    topics = ("kicad", "symbols", "eda", "library", "data")

    # 资源型数据包：非库非应用，显式 unknown 以避免 R38 commands.json 门禁误判
    package_type = "unknown"
    # L0p：OHOS profile 需要 os/compiler/build_type/arch 四项齐备
    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "conandata.yml"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"],
            destination=self.source_folder, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 CMakeLists 用 find_package(Python3 COMPONENTS Interpreter) 驱动
        # tools/kicad_lib_pack.py，找不到就 FATAL_ERROR。R33：显式给出解释器路径，
        # 不依赖构建机上 PATH 的偶然状态（CI 的 build_and_test.sh 自身也用 python3）。
        interpreter = shutil.which("python3") or shutil.which("python")
        if interpreter:
            tc.cache_variables["Python3_EXECUTABLE"] = interpreter
        tc.generate()

    def build(self):
        # 上游 project(... NONE)：无编译器调用，只有 pack_symbols 自定义目标
        # （Python 打包 223 个库），因此交叉/原生构建结果一致。
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.md", self.source_folder,
             self.package_folder + "/licenses")
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 纯资源包：不产出 bin/lib/include，只暴露 share/ 作为资源目录
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.set_property("cmake_file_name", "kicad-symbols")
