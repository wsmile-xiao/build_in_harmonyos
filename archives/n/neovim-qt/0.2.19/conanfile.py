#!/usr/bin/env python3
"""Conan recipe for neovim-qt 0.2.19 — Neovim client library and GUI (Qt5).

neovim-qt 是 Neovim 的 Qt5 GUI 前端（C++，CMake 构建，ISC 许可），提供
libneovim-qt 客户端库 + nvim-qt GUI 可执行文件。

OHOS 适配:
- 依赖制品仓已发布包：qt5-qtbase/5.15.2（Gui/Network/Widgets）、
  qt5-qtsvg/5.15.2、msgpack-c/7.0.0（USE_SYSTEM_MSGPACK=ON 用系统包，
  避免上游 bundled msgpack）、neovim/0.11.3（运行时，tool 依赖）;
- CMake 构建（WITH_QT=Qt5、REPRODUCIBLE_BUILD=ON）;
- 测试: QT_QPA_PLATFORM=offscreen 规避鸿蒙无 X11/Wayland 显示服务器
  （Homebrew 测试先例 QT_QPA_PLATFORM=minimal 同理）。
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, load, save


class NeovimQtConan(ConanFile):
    name = "neovim-qt"
    version = "0.2.19"
    description = "Neovim client library and GUI, in Qt5"
    license = "ISC"
    homepage = "https://github.com/equalsraf/neovim-qt"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

    def requirements(self):
        # Qt5 GUI/Network/Widgets + SVG（制品仓已发布；5.15.2.2 含完整
        # Qt5Widgets，5.15.2 的包 configure -no-widgets 缺 widgets 组件）
        # override: qt5-qtsvg 传递依赖 qt5-qtbase/5.15.2，统一提升到 5.15.2.2
        # （补丁版本，ABI 兼容，Qt5Svg 链接的 Qt5Core/Qt5Gui 符号不变）
        self.requires("qt5-qtbase/5.15.2.2", override=True)
        self.requires("qt5-qtsvg/5.15.2")
        # msgpack（USE_SYSTEM_MSGPACK=ON，避免上游 bundled）
        self.requires("msgpack-c/7.0.0")

    def build_requirements(self):
        # neovim 运行时（编译/测试需要 nvim 可执行文件）
        self.tool_requires("neovim/0.11.3")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"neovim-qt only supports Linux and OHOS, got {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 0001: errorwidget 用 QLabel 替代 QSvgWidget（制品仓 qtsvg 包缺
        # QSvgWidget 符号，见 conandata.yml patch_description）
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["USE_SYSTEM_MSGPACK"] = "ON"
        tc.variables["WITH_QT"] = "Qt5"
        tc.variables["REPRODUCIBLE_BUILD"] = "ON"
        # 上游 find_package(QT NAMES Qt5) 需要 Qt5Config.cmake（聚合配置，
        # 位于 qt5-qtbase 包 lib/cmake/Qt5/），CMakeDeps 只生成组件级
        # Qt5CoreConfig.cmake 等——把 qtbase 与 qtsvg 包根加入前缀路径，
        # 使 find_package(Qt5Svg)（qtsvg 包 lib/cmake/Qt5Svg/）也能命中。
        qtbase_pkg = self.dependencies["qt5-qtbase"].package_folder
        qtsvg_pkg = self.dependencies["qt5-qtsvg"].package_folder
        tc.variables["CMAKE_PREFIX_PATH"] = f"{qtbase_pkg};{qtsvg_pkg}"
        # 制品仓 qtbase 包的 Qt5CoreConfigExtrasMkspecDir.cmake 硬编码了
        # 已删除的构建目录路径 `${_qt5Core_install_prefix}/../b//mkspecs/
        # linux-clang`，find_package(Qt5Core) 的 _qt5_Core_check_file_exists
        # 校验该文件不存在即报错（CI 干净环境从制品仓下载原始包，本地手工
        # 修复不生效）。动态改写为包内实际路径（mkspecs/linux-clang 存在）。
        mkspec_cmake = os.path.join(
            qtbase_pkg, "lib", "cmake", "Qt5Core", "Qt5CoreConfigExtrasMkspecDir.cmake")
        if os.path.exists(mkspec_cmake):
            content = load(self, mkspec_cmake)
            fixed = content.replace(
                "${_qt5Core_install_prefix}/../b//mkspecs/linux-clang",
                "${_qt5Core_install_prefix}/mkspecs/linux-clang")
            if fixed != content:
                save(self, mkspec_cmake, fixed)
                self.output.info(
                    "patched Qt5CoreConfigExtrasMkspecDir.cmake: ../b//mkspecs -> mkspecs")
        # qtbase 聚合 Qt5Config.cmake 用
        #   find_package(Qt5${module} PATHS ${_qt5_module_paths} NO_DEFAULT_PATH)
        # 逐个找组件，_qt5_module_paths 定义在 Qt5ModuleLocation.cmake 中——
        # 制品仓原始包只含 qtbase 自身路径，CI 上 find_package(Qt5Svg) 找不到
        # qtsvg 包的 Qt5SvgConfig.cmake（本地此前手工追加过，CI 干净环境
        # 下载原始包不生效）。动态把 qtsvg 包路径追加进 _qt5_module_paths。
        modloc_cmake = os.path.join(
            qtbase_pkg, "lib", "cmake", "Qt5", "Qt5ModuleLocation.cmake")
        if os.path.exists(modloc_cmake):
            content = load(self, modloc_cmake)
            if qtsvg_pkg not in content:
                content = re.sub(
                    r'set\(_qt5_module_paths ([^)]*)\)',
                    rf'set(_qt5_module_paths \1 {qtsvg_pkg})',
                    content,
                )
                save(self, modloc_cmake, content)
                self.output.info(
                    "patched Qt5ModuleLocation.cmake: appended qtsvg module path")
        # helptags 步骤会运行 nvim 生成 runtime/doc/tags；鸿蒙 restricted
        # kernel 禁止 LuaJIT JIT 代码生成，nvim 启动即 PANIC 崩溃。用无害
        # 的 true 覆盖 NEOVIM_EXEC（CMakeLists 仅当 NEOVIM_EXEC 不存在时
        # 才回退到 nvim），使该 custom command 跳过，构建继续。
        tc.variables["NEOVIM_EXEC"] = "/usr/bin/true"
        tc.generate()

    def build(self):
        # 鸿蒙 restricted kernel 禁止 LuaJIT JIT 代码生成，nvim 运行
        # helptags 命令启动即 PANIC（runtime code generation failed）。
        # 预置空 tags 文件使 make 认为 custom command 输出已存在而跳过
        # （tags 为运行时 help 索引，空文件不影响程序构建与运行）。
        tags = os.path.join(self.build_folder, "src", "gui", "runtime", "doc", "tags")
        os.makedirs(os.path.dirname(tags), exist_ok=True)
        with open(tags, "w", encoding="utf-8"):
            pass
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
