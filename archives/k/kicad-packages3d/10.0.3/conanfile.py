#!/usr/bin/env python3
"""Conan recipe for kicad-packages3d 10.0.3 — KiCad 官方 3D 模型库（数据/资源型包）。

上游事实（已在 PR 中逐条给出证据）：
  * 上游仓库 https://gitlab.com/kicad/libraries/kicad-packages3D，tag 10.0.3；
  * 仓库内容为 105 个 ``*.3dshapes`` 模型目录，共 7238 个 STEP（``*.step``）3D 模型
    文件（供 KiCad 3D 渲染与 MCAD 集成使用；tag 10.0.3 实测**仅含 STEP，0 个 WRL**），
    外加顶层 ``CMakeLists.txt`` / ``CMakeModules/`` / ``LICENSE.md`` / ``README.md``；
  * 上游唯一的构建逻辑是顶层 ``CMakeLists.txt``：``project( kicad-packages3d NONE )``
    —— **没有任何 C/C++ 编译单元**。它只做了两件事：
      1. 用 ``list_models`` 自定义目标（``find``/``realpath``/``sed``/``wc``）统计模型清单与
         ``metrics.txt``；
      2. ``install( DIRECTORY *.3dshapes DESTINATION share/kicad/3dmodels
         FILES_MATCHING PATTERN "*.step" PATTERN ".git" EXCLUDE )`` 把全部 STEP 模型
         安装到 ``share/kicad/3dmodels``。

本配方刻意**使用上游构建系统（CMake）**而不是自己 copy 文件：上游 install() 规则已经
完整表达了“模型目录 → share/kicad/3dmodels 安装 + 仅落 STEP + 排除 .git”的语义，
复用它可以保证产物与上游/发行版一致，并让上游 install 规则成为真实被执行的代码路径。

产物布局与 Debian 官方包 ``kicad-library-packages3d``（10.0.x, all）实测一致：
    share/kicad/3dmodels/<X>.3dshapes/*.step     （各 fp-lib 目录对应的 3D 模型）
    licenses/LICENSE.md

注意：上游 install 规则 ``FILES_MATCHING PATTERN "*.step"`` **只安装 STEP 模型**；
且 tag 10.0.3 仓库内实测**仅含 STEP 文件（0 个 WRL）**。这与 Debian 官方包一致
（KiCad 运行时以 STEP 作为首要 3D 数据源，WRL 仅用于光线追踪渲染，本仓库未收录）。

平台说明：本包不含可执行文件与 C/C++ 产物，因此 package_type 取 unknown 而非
application（后者会被 R38/commands.json 门禁判定为命令行工具包），按资源型数据包处理
（知识库 E255 / E305 同类模式）。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get

required_conan_version = ">=2.0.0"


class KicadPackages3dConan(ConanFile):
    name = "kicad-packages3d"
    version = "10.0.3"
    description = ("Official KiCad 3D model libraries (STEP 3D models for rendering and "
                   "MCAD integration across 100+ model categories); data/resource package "
                   "with no C/C++ library artifact")
    homepage = "https://gitlab.com/kicad/libraries/kicad-packages3D"
    license = "CC-BY-SA-4.0"
    url = ""
    topics = ("kicad", "packages3d", "3dmodels", "eda", "library", "data")

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
        # 上游 project(... NONE)，无编译器、无 find_package(Python) 依赖：
        # 仅生成 CMakeToolchain（Conan 2 把 toolchain 写入 build 目录）。
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        # 上游 project(... NONE)：无编译器调用。cmake.build() 会触发 list_models
        # 自定义目标（find/realpath/sed/wc 统计模型清单与 metrics），交叉/原生构建
        # 结果一致，产物与架构无关。
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
        self.cpp_info.set_property("cmake_file_name", "kicad-packages3d")
