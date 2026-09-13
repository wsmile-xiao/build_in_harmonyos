#!/usr/bin/env python3
"""Conan recipe — conducteo 5.0.2 (Qt6 GUI, HarmonyOS PC aarch64 适配).

热桥计算软件（EN 10211 标准），Qt6 Widgets GUI 应用。CMake 构建，
产出可执行文件 conducteo（bin/）。

OHOS 适配（本 PR）:
- CMakeLists.txt: OHOS 下 CMAKE_SYSTEM_NAME=HarmonyOS 且 CMake 不设 UNIX
  变量 → 平台判断 `if (UNIX AND NOT APPLE)` 全部失效。新增 IS_LINUX_LIKE
  归一化判断（CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" → TRUE），替换 5 处
  平台分支。
- CMakeLists.txt: 依赖库从裸名（uuid/zip/tinyxml）改为 conan 目标
  （uuid::uuid/libzip::libzip/tinyxml::tinyxml），补 find_package。
- QtPrintSupport 裁剪：制品仓 qtbase 的 FEATURE_printsupport=OFF 且无
  QtPrintSupport 头文件；源码中 QPrinter 仅 include 无实体使用，PDF 导出
  实际用 QPdfWriter（QtGui 模块）→ 移除 PrintSupport 组件与冗余 include，
  主功能（PDF 报告导出）零损失。
- DebianInstaller.cmake: 上游 Debian 打包文件（debian/*.desktop/.png/.xml）
  不随源码 tarball 发布 → install 加 EXISTS 保护，数据/文档/示例安装不受影响。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class ConducteoConan(ConanFile):
    name = "conducteo"
    version = "5.0.2"
    description = "conducteo — free software for 2D thermal bridges computation (EN 10211)"
    license = "GPL-3.0"
    homepage = "https://sourceforge.net/projects/conducteo/"
    url = "https://sourceforge.net/projects/conducteo/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 (qtbase 含 Widgets/Core/Gui；PrintSupport 已裁剪)
        self.requires("qtbase/6.11.1.1.1")
        # 数值计算
        self.requires("eigen/3.4.1")
        # 文档/XML/DXF/压缩/JSON/UUID
        self.requires("tinyxml/2.6.2")
        self.requires("dxflib/3.26.4")
        self.requires("libzip/1.11.4")
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("nlohmann_json/3.12.0")
        self.requires("uuid/2.40.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 生成依赖 CMake Config（Eigen3Config.cmake/tinyxml-config.cmake 等），
        # 供 find_package(Eigen3/tinyxml/libzip/uuid/nlohmann_json) 使用
        deps = CMakeDeps(self)
        deps.generate()

        qtbase = self.dependencies["qtbase"]
        qt_prefix = qtbase.package_folder.replace("\\", "/")

        tc = CMakeToolchain(self)
        # R26: system-name libraries default to static
        tc.cache_variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

        # qtbase 包 cmake_find_mode=none，自带 relocatable Qt6Config.cmake，
        # 需手动注入 CMAKE_PREFIX_PATH 指向 qtbase 的 lib/cmake（同 adwaita-qt）。
        # ⚠️ 不能覆盖 CMakeDeps 生成的同名文件：此文件被 conan_toolchain.cmake
        # include，必须保留 generators 目录本身（${CMAKE_CURRENT_LIST_DIR}），
        # 否则 Eigen3/tinyxml 等依赖 Config 找不到（E540 同族坑）。
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w", encoding="utf-8") as handle:
            handle.write(
                "\n".join(
                    [
                        f'list(PREPEND CMAKE_PREFIX_PATH "{qt_prefix}/lib/cmake")',
                        f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_prefix}/lib")',
                        f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_prefix}/include")',
                        'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                        'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                        "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
                    ]
                )
                + "\n"
            )

    def build(self):
        apply_conandata_patches(self)
        # Qt 构建期工具（moc/rcc/qsb）在 OHOS 上运行需加载 libQt6Core.so
        # 及其依赖 libc++_shared.so。conan toolchain 的 LD_LIBRARY_PATH 只含
        # ${qtbase}/lib 与 SDK llvm/lib，缺 aarch64-linux-ohos 子目录中的
        # libc++_shared.so → moc "Error relocating ... symbol not found"。
        # 手动注入 qtbase lib + SDK libc++ 目录（qalculate-gtk 同款做法）。
        # SDK 路径可用环境变量 OHOS_SDK_LLVM_LIB 覆盖（默认取 CI profile 同路径）。
        qtbase = self.dependencies["qtbase"]
        sdk_cxx = os.environ.get(
            "OHOS_SDK_LLVM_LIB",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
            "ohos/native/llvm/lib/aarch64-linux-ohos",
        )
        _lib_dirs = [d for d in [qtbase.package_folder + "/lib", sdk_cxx,
                                 "/system/lib64", "/system/lib"]
                     if os.path.isdir(d)]
        _prev = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            list(dict.fromkeys(_lib_dirs + ([_prev] if _prev else []))))
        self.output.info("LD_LIBRARY_PATH=" + os.environ["LD_LIBRARY_PATH"])
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # GUI 可执行程序，无库文件供下游链接
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))