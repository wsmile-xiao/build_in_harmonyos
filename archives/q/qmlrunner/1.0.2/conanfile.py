#!/usr/bin/env python3
"""Conan recipe — qmlrunner 1.0.2 (Qt5 QML 应用启动器, HarmonyOS PC aarch64).

上游 (rinigus/qmlrunner, GPL-3.0) 是单文件 Qt5 程序：按约定加载
``PREFIX/appname/qml/appname.qml`` 作为窗口，并支持翻译 (``PREFIX/appname/
translations/appname-LOCALE.qm``) 与回退图标 (``PREFIX/appname/icons``)。

上游构建系统: qmake (qmlrunner.pro: QT += quick qml widgets)。

OHOS 适配:
  - qmake(.pro) → 自研 CMakeLists.txt（patch 新增）：手动接线 Qt5 的
    include/lib 目录（qt5-qtbase/5.15.2.2 + qt5-qtdeclarative/5.15.2），
    与 diffpdf 配方同模式（该 Qt 打包未接 CMakeDeps config）。
  - main.cpp 无 Q_OBJECT/qrc，不需要 moc/rcc。
  - 平台说明：OHOS PC 无 X11/Wayland 平台插件运行时保证，qt5-qtbase
    提供 offscreen/minimal/vnc 平台插件；test_package 以
    QT_QPA_PLATFORM=offscreen + QT_QUICK_BACKEND=software 做功能级验证
    （QML 窗口加载 + 事件循环 + 退出码），见 test_package/test.sh。
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class QmlrunnerConan(ConanFile):
    name = "qmlrunner"
    version = "1.0.2"
    description = "Runner for QML-only apps — loads prefix/appname/qml/appname.qml as a Qt5 window"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/rinigus/qmlrunner"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"  # 可执行文件（R38: 需要 commands.json）
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt5 基础模块（Core/Gui/Widgets）
        self.requires("qt5-qtbase/5.15.2.2")
        # QtQml / QtQuick（QQmlApplicationEngine 在 Qt5Qml，QQuickWindow 在 Qt5Quick）
        self.requires("qt5-qtdeclarative/5.15.2")

    def validate(self):
        # R32: settings.os 判断用 in
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"qmlrunner only supports Linux and OHOS, got {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        # 官方源 tarball 顶层目录为 qmlrunner-1.0.2/，strip_root 拉平。
        # url 兼容字符串与列表两种形态（CI 会把已知域名改写为镜像列表，
        # Conan 2 逐项回退；参考 qt5-qtbase 配方写法）。
        source_data = self.conan_data["sources"]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                # codeload URL 以 tag 名结尾（无扩展名），必须显式传
                # filename，否则 Conan get() 会退回 zip 解码器并抛
                # BadZipFile（mbrola/abcmidi 配方同款注释）。
                get(self, url=url, sha256=source_data["sha256"],
                    filename="qmlrunner-1.0.2.tar.gz", strip_root=True)
                return
            except ConanException as error:
                self.output.warning(
                    f"Failed to download qmlrunner source from {url}: {error}"
                )
        raise ConanException("Unable to download qmlrunner source from all URLs")

    def generate(self):
        qtbase = self.dependencies["qt5-qtbase"]
        qml = self.dependencies["qt5-qtdeclarative"]

        # Qt5 头文件布局：模块转发头要求 include/ 与 include/<Module>/ 双路径。
        include_dirs = []
        for dep, modules in (
            (qtbase, ("QtCore", "QtGui", "QtWidgets")),
            (qml, ("QtQml", "QtQuick")),
        ):
            inc = os.path.join(dep.package_folder, "include")
            if os.path.isdir(inc):
                include_dirs.append(inc)
            for module in modules:
                module_dir = os.path.join(inc, module)
                if os.path.isdir(module_dir):
                    include_dirs.append(module_dir)

        lib_dirs = [
            d for d in (
                os.path.join(qtbase.package_folder, "lib"),
                os.path.join(qml.package_folder, "lib"),
            ) if os.path.isdir(d)
        ]

        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # E092: CMake 无 HarmonyOS 平台文件，映射为 OHOS.cmake
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.variables["QMLRUNNER_QT5_INCLUDE_DIRS"] = ";".join(include_dirs)
        tc.variables["QMLRUNNER_QT5_LIB_DIRS"] = ";".join(lib_dirs)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 可执行程序包：无库文件供下游链接；将 bin 注入运行环境 PATH
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
