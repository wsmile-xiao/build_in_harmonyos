#!/usr/bin/env python3
"""Conan recipe for Flameshot 14.0.0 on OpenHarmony PC.

Flameshot is a Qt5 C++ screenshot application with markup tools. The
recipe builds the GUI binary (and the CLI entry) with the Qt5 toolchain
from the registry. Qt5 LinguistTools is not shipped by qt5-qtbase in the
registry, so the two upstream CMakeLists are patched to drop the
find_package requirement and skip .ts translation generation.

The two FetchContent dependencies (Qt-Color-Widgets, KDSingleApplication)
are fetched from their official sources during source() and placed in
external/ so the build never needs network access.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)


class FlameshotConan(ConanFile):
    name = "flameshot"
    version = "14.0.0"
    description = "Powerful yet simple to use screenshot software"
    license = "GPL-3.0-only"
    homepage = "https://flameshot.org"
    url = "https://github.com/flameshot-org/flameshot"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qt5-qtsvg 上游配方硬编码依赖 qt5-qtbase/5.15.2；flameshot 需要带
        # DBus 模块的 qt5-qtbase/5.15.2.2（qt5-qtbase/5.15.2 为 -no-dbus
        # 构建）。用 override 强制 5.15.2.2（组件 API 与 5.15.2 兼容），
        # 并显式 headers=True 使 CMakeDeps 导出 Qt5 头文件路径。
        self.requires("qt5-qtbase/5.15.2.2", headers=True, override=True)
        self.requires("qt5-qtsvg/5.15.2.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # FetchContent dependencies, placed under external/ so CMake's
        # add_subdirectory branch is taken (no network at build time).
        external = os.path.join(self.source_folder, "external")
        os.makedirs(external, exist_ok=True)
        qcw = self.conan_data["external"]["qt-color-widgets"]
        get(
            self,
            url=qcw["url"],
            sha256=qcw["sha256"],
            strip_root=True,
            filename="qt-color-widgets.tar.gz",
            destination=os.path.join(external, "Qt-Color-Widgets"),
        )
        kdsa = self.conan_data["external"]["kdsingleapplication"]
        get(
            self,
            url=kdsa["url"],
            sha256=kdsa["sha256"],
            strip_root=True,
            destination=os.path.join(external, "KDSingleApplication"),
        )
        apply_conandata_patches(self)

    def generate(self):
        deps = CMakeDeps(self)
        # flameshot 的 CMake 用 find_package(Qt5) + Qt5:: 目标；qt5-qtbase
        # 的组件已声明 Qt5Core 等 cmake_file_name，顶层统一映射为 Qt5。
        # qt5-qtsvg 组件自带 Qt5Svg cmake_file_name（Qt5::Svg），不覆盖，
        # 否则 Qt5SvgConfig.cmake 不会生成导致 Qt5::Svg 找不到。
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["QT_DEFAULT_MAJOR_VERSION"] = "5"
        tc.variables["QT_VERSION_MAJOR"] = "5"
        tc.variables["USE_KDSINGLEAPPLICATION"] = "ON"
        tc.variables["USE_BUNDLED_KDSINGLEAPPLICATION"] = "ON"
        tc.variables["DISABLE_UPDATE_CHECKER"] = "ON"
        tc.variables["ENABLE_IMGUR"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"
        # OHOS SDK 的 ohos.toolchain.cmake 设置
        # CMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY，find_package(Qt5) 只会
        # 在 SDK find-root 内查找，CMakeDeps 生成的 Qt5Config.cmake 位于
        # generators 目录会被忽略。放开为 BOTH 并保留 CMAKE_PREFIX_PATH，
        # 使 Qt5 配置能被找到。
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        # OHOS SDK toolchain 设置 CMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY
        #（普通变量，命令行 -D 的 BOTH 会被其覆盖），find_package 只在
        # CMAKE_FIND_ROOT_PATH 内查找。把 generators 目录加入
        # CMAKE_FIND_ROOT_PATH（toolchain 会 list(APPEND) SDK 路径），
        # 使 CMakeDeps 生成的 Qt5/dbus 等配置可被找到；Qt5_DIR 显式
        # 指向 generators 作为兜底。
        qt5 = self.dependencies["qt5-qtbase"].package_folder
        # qt5-qtbase enters the graph via an override, so CMakeDeps leaves
        # the Qt5 component include paths empty. Collect the include root
        # and all Qt* subdirs (code uses both <QtCore/QObject> and plain
        # <QWidget> include forms); the 0005 patch consumes the list.
        qt5_inc = os.path.join(qt5, "include")
        qt5_incs = [qt5_inc]
        if os.path.isdir(qt5_inc):
            qt5_incs.extend(
                os.path.join(qt5_inc, name)
                for name in sorted(os.listdir(qt5_inc))
                if os.path.isdir(os.path.join(qt5_inc, name))
            )
        cmake.configure(
            variables={
                "Qt5_DIR": self.generators_folder,
                "CMAKE_PREFIX_PATH": self.generators_folder,
                "CMAKE_FIND_ROOT_PATH": self.generators_folder,
                "KDSingleApplication_QT6": "OFF",
                "QT_VERSION_MAJOR": "5",
                "QT_DEFAULT_MAJOR_VERSION": "5",
                # CMakeDeps does not export Qt5::moc/Qt5::rcc/Qt5::uic
                # executable targets; point AUTOMOC/AUTORCC/AUTOUIC at the
                # qt5-qtbase tools.
                "CMAKE_AUTOMOC_EXECUTABLE": os.path.join(qt5, "bin", "moc"),
                "CMAKE_AUTORCC_EXECUTABLE": os.path.join(qt5, "bin", "rcc"),
                "CMAKE_AUTOUIC_EXECUTABLE": os.path.join(qt5, "bin", "uic"),
                # The OHOS SDK toolchain points CMAKE_RANLIB at a missing
                # llvm-ranlib; the host wrapper at /data/service/hnp/bin is
                # available and works with the SDK archiver.
                "CMAKE_AR": "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/llvm-ar",
                "CMAKE_RANLIB": "/data/service/hnp/bin/llvm-ranlib",
                "FLAMESHOT_QT5_INCLUDE_DIR": ";".join(qt5_incs),
                # Same override limitation: CMakeDeps does not export the
                # Qt5 component link libraries either, so link.txt only
                # carries libQt5Svg.so. Append the Qt5 lib dir and libs
                # explicitly (also needed during CMake TryCompile probes).
                "CMAKE_EXE_LINKER_FLAGS": "-L{0}/lib -lQt5Core -lQt5Gui -lQt5Widgets -lQt5Network -lQt5DBus".format(qt5),
            }
        )
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        rmdir(self, os.path.join(self.package_folder, "share", "applications"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
