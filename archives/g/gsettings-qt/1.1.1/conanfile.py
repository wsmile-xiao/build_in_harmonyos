#!/usr/bin/env python3
"""Conan recipe — gsettings-qt 1.1.1（CMake + Qt6）on HarmonyOS PC.

上游：https://gitlab.com/ubports/development/core/gsettings-qt
产物：libgsettings-qt6.so（Qt 绑定 GSettings）+ QML 插件（GSettings 1.1）+ pkg-config 元数据。

HarmonyOS PC 适配要点
--------------------
1. 上游默认构建 Qt5（ENABLE_QT6=OFF），本配方固定 -DENABLE_QT6=ON：
   OHOS 侧 Qt 生态与下游消费方（例如 libkysdk-desktop 的 Qt6 变体）均为 Qt6。
2. Qt6 模块 config 必须用依赖包内的原生文件：qtbase 的 Qt6Config.cmake 与
   qtdeclarative 的 Qt6QmlConfig.cmake。二者配方已声明 cmake_find_mode=none，
   故本配方把 qtbase 放进 CMAKE_PREFIX_PATH、qtdeclarative 放进
   QT_ADDITIONAL_PACKAGES_PREFIX_PATH（Qt 只在其附加前缀里找模块 config）。
3. GSettings/CMakeLists.txt 使用 cmake-extras 提供的 QmlPlugins 模块
   （find_package(QmlPlugins REQUIRED) + add_qmlplugin），其包目录需进
   CMAKE_PREFIX_PATH。
4. configure 阶段的 find_program(qmlplugindump REQUIRED) 以及
   QmlPluginsConfig.cmake 内部的同名查找都要求 qmlplugindump 在 PATH 上；
   测试阶段的 find_program(glib-compile-schemas REQUIRED) 同理。故构建环境显式
   注入 qtdeclarative/bin、glib/bin、qtbase/bin 并补齐 LD_LIBRARY_PATH——这些
   工具是 OHOS arm64 本机可执行文件，构建机即 OHOS arm64，可直接运行。
5. CMake 不存在 Platform/HarmonyOS.cmake：本工程只用标准平台规则，故把平台
   呈现为 Linux（与本仓库 qtdeclarative 配方同一处理）。
6. gio-2.0 / glib-2.0 由 pkg-config 解析（上游 pkg_check_modules），
   PkgConfigDeps 从 glib 包组件生成 .pc 并注入 PKG_CONFIG_PATH。
7. OHOS 要求 ELF 带代码签名：构建树内测试可执行文件、插件与安装后的
   .so 均在运行/打包前自签名。
"""

import os
import shlex
import shutil
import stat
import subprocess
import tempfile
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps


class GsettingsQtConan(ConanFile):
    name = "gsettings-qt"
    version = "1.1.1"
    description = "Qt6 bindings to GSettings (libgsettings-qt6 + QML module GSettings 1.1)"
    license = "LGPL-3.0-only"
    homepage = "https://gitlab.com/ubports/development/core/gsettings-qt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 Core：qgsettings.h 对外暴露 QObject/QStringList，且库链接 Qt6Core。
        self.requires("qtbase/6.11.1", transitive_headers=True, transitive_libs=True)
        # Qt6 Qml：QML 插件 GSettingsQmlPlugin 链接 Qt6Qml；测试用 Qt6QuickTest。
        self.requires("qtdeclarative/6.11.1", transitive_libs=True)
        # gio-2.0：库源码含 <gio/gio.h>，gsettings-qt6.pc 声明 Requires: gio-2.0。
        self.requires("glib/2.88.3", transitive_libs=True)

    def build_requirements(self):
        # find_package(PkgConfig REQUIRED)：制品仓 pkgconf 同时提供 pkg-config 别名。
        self.tool_requires("pkgconf/3.0.6")
        # QmlPlugins.cmake / add_qmlplugin（纯 CMake 模块数据包，构建期使用，
        # 不进入消费者的依赖链）。
        self.tool_requires("cmake-extras/1.9")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()

        qtbase = self.dependencies["qtbase"].package_folder
        qtdeclarative = self.dependencies["qtdeclarative"].package_folder
        qtshadertools = self.dependencies["qtshadertools"].package_folder
        cmake_extras = self.dependencies.build["cmake-extras"].package_folder

        tc = CMakeToolchain(self)

        # CMake 没有 Platform/HarmonyOS.cmake；按 Linux 平台规则构建，OHOS clang
        # 驱动本身仍生成 aarch64-linux-ohos 目标（与 qtdeclarative 配方同源处理）。
        class OhosLinuxPlatformBlock(Block):
            template = textwrap.dedent(
                """\
                # Treat the HarmonyOS host as Linux for CMake platform rules.
                set(CMAKE_SYSTEM_NAME Linux)
                set(CMAKE_HOST_SYSTEM_NAME Linux)
                set(CMAKE_CROSSCOMPILING FALSE)
                set(CMAKE_SYSTEM_PROCESSOR aarch64)
                set(CMAKE_HOST_SYSTEM_PROCESSOR aarch64)
                """
            )

            def context(self):
                return {}

        tc.blocks["user_toolchain"] = OhosLinuxPlatformBlock

        tc.cache_variables.update(
            {
                "CMAKE_PREFIX_PATH": ";".join([qtbase, cmake_extras]),
                "QT_ADDITIONAL_PACKAGES_PREFIX_PATH": ";".join(
                    [qtdeclarative, qtshadertools]
                ),
                "QT_QMAKE_TARGET_MKSPEC": "harmonyos-clang",
                "ENABLE_QT6": "ON",
                "ENABLE_WERROR": "OFF",
                "BUILD_TESTING": "ON",
            }
        )
        tc.generate()

        # 构建期工具（qmlplugindump / glib-compile-schemas）与运行期库路径。
        env = Environment()
        for package in ("qtbase", "qtdeclarative", "glib", "qtshadertools"):
            prefix = self.dependencies[package].package_folder
            env.prepend_path("PATH", os.path.join(prefix, "bin"))
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "lib"))
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        # QML 运行期导入路径：上游 qmltest 只用 QML2_IMPORT_PATH=构建树（其
        # set_tests_properties 会覆盖同名环境变量），而 QtTest/TestCase.qml 需要
        # QtQuick.Window 等模块 → 用 QML_IMPORT_PATH 补充依赖包内的 QML 模块目录
        # （Qt6 同时读取这两个变量，前者不被测试属性覆盖）。
        for package in ("qtdeclarative", "qtbase", "qtshadertools"):
            prefix = self.dependencies[package].package_folder
            env.prepend_path("QML_IMPORT_PATH", os.path.join(prefix, "qml"))
        env.vars(self).save_script("conanbuild_gsettings_qt_env")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._sign_build_tree_elfs()
        self._run_upstream_tests()

    # ── 上游测试（tests/CMakeLists.txt 注册的 ctest 用例）──────────────

    def _run_upstream_tests(self):
        """GSettings Schema 由 glib-compile-schemas 在构建树内生成，
        schema 目录/后端等环境由上游 set_tests_properties 指定。"""
        self.run(
            "ctest --test-dir {} --output-on-failure --parallel 1".format(
                shlex.quote(self.build_folder)
            ),
            env="conanbuild",
            ignore_errors=False,
        )

    # ── OHOS ELF 签名 ────────────────────────────────────────────────

    def _sign_build_tree_elfs(self):
        """测试可执行文件与 QML 插件在运行/安装前必须带 OHOS 代码签名。"""
        if str(self.settings.os) != "OHOS":
            return
        for root, _, filenames in os.walk(self.build_folder):
            for filename in filenames:
                candidate = os.path.join(root, filename)
                if os.path.islink(candidate) or not os.access(candidate, os.X_OK):
                    continue
                if self._elf_type(candidate) in (2, 3):  # ET_EXEC / ET_DYN
                    self._sign_elf(candidate)

    def _sign_installed_elfs(self):
        for root, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                candidate = os.path.join(root, filename)
                if os.path.islink(candidate):
                    continue
                if self._elf_type(candidate) in (2, 3):
                    self._sign_elf(candidate)

    def _sign_elf(self, path):
        objcopy = self._resolve_tool("OBJCOPY", "llvm-objcopy")
        objdump = self._resolve_tool("OBJDUMP", "llvm-objdump")
        signer = self._resolve_tool("BINARY_SIGN_TOOL", "binary-sign-tool")
        original_mode = stat.S_IMODE(os.stat(path).st_mode)
        with tempfile.TemporaryDirectory(
            prefix=".conan-sign-", dir=os.path.dirname(path)
        ) as temp_dir:
            sign_input = path
            if self._has_codesign_section(objdump, path):
                sign_input = os.path.join(temp_dir, "unsigned")
                shutil.copy2(path, sign_input)
                self._run_tool([objcopy, "--remove-section", ".codesign", sign_input])
            signed = os.path.join(temp_dir, "signed")
            self._run_tool(
                [
                    signer,
                    "sign",
                    "-inFile",
                    sign_input,
                    "-outFile",
                    signed,
                    "-selfSign",
                    "1",
                ]
            )
            if not os.path.isfile(signed) or not self._has_codesign_section(
                objdump, signed
            ):
                raise ConanInvalidConfiguration(
                    f"Signing did not produce a signed ELF for {path}"
                )
            os.replace(signed, path)
            os.chmod(path, original_mode)

    def _has_codesign_section(self, objdump, path):
        return ".codesign" in self._run_tool([objdump, "-h", path])

    @staticmethod
    def _elf_type(path):
        try:
            with open(path, "rb") as binary:
                header = binary.read(18)
        except OSError:
            return None
        if len(header) < 18 or header[:4] != b"\x7fELF":
            return None
        byte_order = {1: "little", 2: "big"}.get(header[5])
        if byte_order is None:
            return None
        return int.from_bytes(header[16:18], byte_order)

    @staticmethod
    def _run_tool(command):
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanInvalidConfiguration(f"{command[0]} failed: {error}") from error
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ConanInvalidConfiguration(f"{command[0]} failed: {detail}")
        return result.stdout

    @staticmethod
    def _resolve_tool(environment_variable, executable):
        candidate = os.environ.get(environment_variable) or executable
        resolved = shutil.which(candidate)
        if not resolved and os.path.isfile(candidate):
            resolved = os.path.abspath(candidate)
        if not resolved:
            raise ConanInvalidConfiguration(
                f"Required tool {executable} not found; set {environment_variable}"
            )
        return resolved

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.libs = ["gsettings-qt6"]
        # 头文件安装到 <prefix>/include/<arch>/qt6/QGSettings（上游用
        # CMAKE_INSTALL_FULL_INCLUDEDIR + CMAKE_LIBRARY_ARCHITECTURE）。
        self.cpp_info.includedirs = [self._qt_include_dir()]
        self.cpp_info.requires = [
            "qtbase::core",
            "qtdeclarative::qml",
            "glib::gio",
        ]
        self.cpp_info.set_property("pkg_config_name", "gsettings-qt6")

    def _qt_include_dir(self):
        # 上游把 qgsettings.h 与转发头文件 QGSettings 一并装到
        # <prefix>/include/<arch>/qt6/QGSettings/，且 .pc 的 Cflags 也指向该目录：
        # 消费方写 #include <QGSettings>，故 include 目录是该 QGSettings 目录本身。
        for root, _, files in os.walk(os.path.join(self.package_folder, "include")):
            if "qgsettings.h" in files:
                return os.path.relpath(root, self.package_folder)
        return "include"
