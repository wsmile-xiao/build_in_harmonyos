#!/usr/bin/env python3
"""Conan recipe — gsettings-qt5 1.1.1（CMake + Qt5）on HarmonyOS PC.

上游：https://gitlab.com/ubports/development/core/gsettings-qt
产物：libgsettings-qt.so（Qt5 绑定 GSettings）+ QML 插件（GSettings 1.1）+
      pkg-config 元数据（gsettings-qt.pc）。

与同上游的 Qt6 变体包 archives/g/gsettings-qt/1.1.1 的关系
--------------------------------------------------------
上游 1.1.1 默认构建 Qt5（`option(ENABLE_QT6 OFF)`），Qt6 变体包显式打开
`ENABLE_QT6=ON`。制品仓已有的 gsettings-qt/1.1.1 是 Qt6 构建，其
libgsettings-qt6.so 无法被 Qt5 程序链接（QObject/QVariant/信号槽 ABI 不同）。
下游 kylin-calendar/5.0.0.0 是 Qt5 程序（`pkg_check_modules(Gsetting REQUIRED
gsettings-qt)` + `#include <QGSettings>`），因此本包按上游默认方式构建 Qt5 链，
产出 `libgsettings-qt.so` 与 `gsettings-qt.pc`（Qt5 下库名/元数据名不带版本后缀）。

HarmonyOS PC 适配要点
--------------------
1. 上游 Qt5 分支：`ENABLE_QT6=OFF`（默认）→ 库名 `gsettings-qt`、`.pc` 名
   `gsettings-qt.pc`、安装头到 `include/<triplet>/qt5/QGSettings/`。
2. Qt5 的 CMake 配置在制品仓被拆到多个包：qt5-qtbase 提供 Qt5::Core/
   Qt5::Test/… 与 AUTOMOC 工具链，qt5-qtdeclarative **没有**原生
   Qt5QmlConfig.cmake（其 package_info 只声明 cmake_file_name=Qt5Qml，
   CMakeDeps 生成单个 Qt5QmlConfig.cmake）。因此 generate() 用一个 Qt5 umbrella
   bridge 覆盖 generators 里的 Qt5Config.cmake：先 include CMakeDeps 的基座
   配置，再补 (a) AUTOMOC 所需的 moc 目标/Qt 版本变量、(b) Qml/QuickTest 分派、
   (c) 上游使用的无版本前缀目标 `Qt::Core`/`Qt::Qml`/`Qt::Test`/`Qt::QuickTest`。
3. GSettings/CMakeLists.txt 以 `find_package(QmlPlugins REQUIRED)` +
   `find_program(qmlplugindump REQUIRED)` 生成 QML 类型元数据；OHOS 的 Qt5 链
   不存在 qmlplugindump（qt5-qtdeclarative 包无 bin/）。补丁 0001 让该查找可选：
   缺失时给出占位 target 并跳过（可选的）plugins.qmltypes 生成，QML 插件本体照常构建。
4. 构建期工具与运行期库路径：glib 提供 `bin/glib-compile-schemas`（测试 schema）、
   qt5-qtbase 提供 `bin/moc`；测试可执行文件的 Qt5 运行库由 LD_LIBRARY_PATH 补齐，
   QML 测试的模块导入路径由 QML_IMPORT_PATH 指向 qt5-qtdeclarative 的 qml/。
5. CMake 不存在 Platform/HarmonyOS.cmake：本工程只用标准平台规则，故把平台
   呈现为 Linux（与本仓库 qt5-qtbase / qt6 qtdeclarative 配方同一处理）。
6. gio-2.0 / glib-2.0 由 pkg-config 解析（上游 pkg_check_modules），
   PkgConfigDeps 从 glib 包组件生成 .pc 并注入 PKG_CONFIG_PATH。
7. OHOS 要求 ELF 带代码签名：构建树内测试可执行文件、插件与安装后的 .so
   均在运行/打包前自签名。
"""

import os
import re
import shlex
import shutil
import stat
import subprocess
import tempfile
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.gnu import PkgConfigDeps


class GsettingsQt5Conan(ConanFile):
    name = "gsettings-qt5"
    version = "1.1.1"
    description = "Qt5 bindings to GSettings (libgsettings-qt + QML module GSettings 1.1)"
    license = "LGPL-3.0-only"
    homepage = "https://gitlab.com/ubports/development/core/gsettings-qt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt5 Core：qgsettings.h 对外暴露 QObject/QStringList/QVariant，库链接
        # libQt5Core；同理提供 Qt5::Test 供上游 cpptest。
        self.requires("qt5-qtbase/5.15.2.2", transitive_headers=True, transitive_libs=True)
        # Qt5 Qml：QML 插件 GSettingsQmlPlugin 链接 Qt5Qml；上游 qmltest 用
        # Qt5QuickTest。二者都打包在同一 qt5-qtdeclarative 里。
        self.requires("qt5-qtdeclarative/5.15.2", transitive_libs=True)
        # gio-2.0：库源码含 <gio/gio.h>，gsettings-qt.pc 声明 Requires: gio-2.0。
        # 版本必须是 glib/2.88.0：Qt5 链的 qt5-qtbase/5.15.2.2 精确依赖 zlib/1.3.1，
        # 而 glib/2.88.3.x 依赖 zlib/1.3.2 —— 二者在 Conan 依赖图里硬冲突
        # （glib/2.88.0 同样依赖 zlib/1.3.1，整链 package_id 与制品仓二进制一致，
        # 无需从源码重建 qt5-qtbase）。
        self.requires("glib/2.88.0", transitive_libs=True)

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
        CMakeDeps(self).generate()

        qtbase = self.dependencies["qt5-qtbase"].package_folder
        cmake_extras = self.dependencies.build["cmake-extras"].package_folder

        tc = CMakeToolchain(self)

        # CMake 没有 Platform/HarmonyOS.cmake；按 Linux 平台规则构建，OHOS clang
        # 驱动本身仍生成 aarch64-linux-ohos 目标（与 qt5-qtbase 配方同源处理）。
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
                # cmake-extras 是纯 CMake 模块数据包（tool_requires），CMakeDeps
                # 不为它生成配置文件 → 直接把包目录加入前缀路径，供
                # GSettings/CMakeLists.txt 的 find_package(QmlPlugins REQUIRED) 命中。
                "CMAKE_PREFIX_PATH": cmake_extras,
                "ENABLE_QT6": "OFF",
                "ENABLE_WERROR": "OFF",
                "BUILD_TESTING": "ON",
            }
        )
        tc.generate()

        # Conan 的 zlib/1.3.1 是「非 PIC 静态」libz.a，链进共享库必然报
        # R_AARCH64 relocation；OHOS 的 Qt5 链本身用的就是系统 libz.so
        # （libQt5Core.so 的 DT_NEEDED 含 libz.so）。这里把该静态库从链接路径里
        # 摘掉，让 `-lz` 命中 OHOS sysroot 里的系统 libz.so。
        self._use_system_zlib()

        # CMakeDeps 生成的是「无组件分派」的 Qt5Config.cmake，覆盖为 umbrella bridge。
        self._write_qt5_bridge(qtbase)

        # 构建期工具（moc / glib-compile-schemas）与运行期库 / QML 模块路径。
        env = Environment()
        for package in ("qt5-qtbase", "qt5-qtdeclarative", "glib"):
            prefix = self.dependencies[package].package_folder
            env.prepend_path("PATH", os.path.join(prefix, "bin"))
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "lib"))
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        # 上游 qmltest 需要 QtTest/QtQuick 等 QML 模块，而 Qt5 的 QML 引擎
        # **只读** QML2_IMPORT_PATH（不读 QML_IMPORT_PATH），且上游
        # set_tests_properties 把它固定为 ${CMAKE_BINARY_DIR} —— 故改由
        # _stage_qml_import_modules() 把 qt5-qtdeclarative 的 qml/ 模块软链进
        # 构建树，使该固定导入路径即可解析（不改上游文件、不改依赖包）。
        # OHOS 受限内核拒绝 mprotect(PROT_EXEC)，Qt5 的 QML V4 引擎基线 JIT 会
        # 因此崩溃（"mprotect failed in ExecutableAllocator::makeExecutable"）；
        # 上游为这类平台预留了 QV4_FORCE_INTERPRETER 开关，改用解释器执行。
        env.define("QV4_FORCE_INTERPRETER", "1")
        env.vars(self).save_script("conanbuild_gsettings_qt5_env")

    # ── 系统 libz.so（替代非 PIC 的 Conan 静态 zlib）────────────────────

    def _use_system_zlib(self):
        """让链接走 OHOS 系统 libz.so，而不是 Conan 的非 PIC 静态 libz.a。

        已发布到制品仓的 zlib/1.3.1 是 `./configure --static`（无 -fPIC）产物，
        其对象不能链进共享库（E541）；而 OHOS 的 Qt5 链本身就是用系统 libz.so
        （libQt5Core.so 带 DT_NEEDED libz.so）。两处需要处理：

        1. zlib.pc（PkgConfigDeps 生成）的 Libs 里写着 Conan 包的 libdir
           （`-L"${libdir}" -lz`）→ 改为纯 `-lz`；
        2. conan_toolchain.cmake 把每个依赖的 libdir 前置进 CMAKE_LIBRARY_PATH，
           CMake 的 FindPkgConfig 会用 find_library() 把 `-lz` 解析成绝对路径，
           从而命中 Conan 的 libz.a → 从 CMAKE_LIBRARY_PATH 里摘掉 zlib 的 libdir，
           使 find_library() 回落到 OHOS sysroot 的系统 libz.so。

        CMakeDeps 侧的 zlib::zlib 目标由 Qt5 bridge 置空（见 _write_qt5_bridge），
        避免 Qt5::Core 注入静态 libz.a。
        """
        pc = os.path.join(self.generators_folder, "zlib.pc")
        if os.path.isfile(pc):
            with open(pc, encoding="utf-8") as handle:
                content = handle.read()
            fixed = re.sub(r"(?m)^Libs:.*$", "Libs: -lz", content)
            if fixed != content:
                save(self, pc, fixed)
                self.output.info("zlib.pc: dropped the Conan static libz.a search path")

        zlib_dep = self.dependencies.get("zlib")
        if not zlib_dep or not zlib_dep.package_folder:
            return
        libdirs = [
            os.path.join(zlib_dep.package_folder, libdir).replace("\\", "/")
            for libdir in (zlib_dep.cpp_info.libdirs or ["lib"])
        ]
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if not os.path.isfile(toolchain):
            return
        with open(toolchain, encoding="utf-8") as handle:
            lines = handle.read().splitlines(keepends=True)
        changed = False
        for index, line in enumerate(lines):
            if line.startswith("list(PREPEND CMAKE_LIBRARY_PATH"):
                updated = line
                for libdir in libdirs:
                    updated = updated.replace('"{}" '.format(libdir), "")
                    updated = updated.replace('"{}"'.format(libdir), "")
                if updated != line:
                    lines[index] = updated
                    changed = True
        if changed:
            save(self, toolchain, "".join(lines))
            self.output.info(
                "conan_toolchain.cmake: zlib libdir removed from CMAKE_LIBRARY_PATH"
            )

    # ── Qt5 umbrella bridge ──────────────────────────────────────────

    def _write_qt5_bridge(self, qtbase):
        """把 CMakeDeps 生成的 Qt5Config.cmake 换成能跨包分派组件的 bridge。

        CMakeToolchain 生成的 conan_toolchain.cmake 会把 generators 目录
        前置到 CMAKE_PREFIX_PATH，因此 generators 里的 Qt5Config.cmake 必然
        赢得 find_package(Qt5 COMPONENTS ...)。这里把 CMakeDeps 的原文件改名为
        Qt5ConanBaseConfig.cmake，再由 bridge include 它，随后补齐 Qt5 生态在本
        制品仓「拆包」下缺失的三类内容（AUTOMOC 工具链 / Qml+QuickTest 分派 /
        无版本前缀 Qt:: 目标）。
        """
        generators = self.generators_folder
        base_config = os.path.join(generators, "Qt5Config.cmake")
        if not os.path.isfile(base_config):
            raise ConanInvalidConfiguration(
                "CMakeDeps did not generate Qt5Config.cmake for the Qt5 chain"
            )
        os.replace(base_config, os.path.join(generators, "Qt5ConanBaseConfig.cmake"))

        moc = os.path.join(qtbase, "bin", "moc")
        bridge = textwrap.dedent(
            """\
            # Auto-generated Qt5 umbrella bridge for the Conan Qt5 package split.
            # Base components (Core/Test/Gui/...) + their transitive deps come from
            # the CMakeDeps-generated qt5-qtbase config; Qml/QuickTest live in the
            # qt5-qtdeclarative package and are dispatched below.

            # Conan's zlib/1.3.1 is a non-PIC static archive that cannot be linked
            # into a shared library; the OHOS Qt5 stack links the system libz.so
            # instead (libQt5Core.so carries DT_NEEDED libz.so). Neutralise the
            # CMakeDeps zlib target before the base config pulls it in, so Qt5::Core
            # stops injecting the static libz.a (the actual `-lz` comes from the
            # rewritten zlib.pc and resolves to the OHOS sysroot libz.so).
            set(zlib_FOUND TRUE)
            if(NOT TARGET zlib::zlib)
                add_library(zlib::zlib INTERFACE IMPORTED)
            endif()

            include("${CMAKE_CURRENT_LIST_DIR}/Qt5ConanBaseConfig.cmake")
            set(Qt5_FOUND TRUE)

            # 1) AUTOMOC tooling: upstream sets CMAKE_AUTOMOC ON, but the CMakeDeps
            #    config exposes neither the moc executable target nor the Qt version
            #    variables CMake's AUTOGEN uses to recognise the Qt version.
            if(NOT TARGET Qt5::moc)
                add_executable(Qt5::moc IMPORTED)
                set_target_properties(Qt5::moc PROPERTIES IMPORTED_LOCATION "@MOC@")
            endif()
            set(Qt5Core_MOC_EXECUTABLE Qt5::moc)
            set(QT_MOC_EXECUTABLE "@MOC@")
            set(Qt5Core_VERSION_MAJOR 5)
            set(Qt5Core_VERSION_MINOR 15)
            set(Qt5Core_VERSION_PATCH 2)
            set(Qt5Core_VERSION_STRING "5.15.2")

            # 2) Cross-package components shipped by qt5-qtdeclarative. Its single
            #    CMakeDeps config (Qt5QmlConfig.cmake) declares the package-level
            #    Qt5::Qml target, which already links every qtdeclarative library
            #    (incl. libQt5QuickTest); QuickTest additionally needs Qt5::Test.
            foreach(_qt5_bridge_comp ${Qt5_FIND_COMPONENTS})
                if(_qt5_bridge_comp STREQUAL "Qml")
                    if(NOT TARGET Qt5::Qml)
                        find_package(Qt5Qml CONFIG QUIET)
                    endif()
                    if(TARGET Qt5::Qml)
                        set(Qt5_Qml_FOUND TRUE)
                    endif()
                elseif(_qt5_bridge_comp STREQUAL "QuickTest")
                    if(NOT TARGET Qt5::Qml)
                        find_package(Qt5Qml CONFIG QUIET)
                    endif()
                    if(TARGET Qt5::Qml AND NOT TARGET Qt5::QuickTest)
                        add_library(Qt5::QuickTest INTERFACE IMPORTED)
                        set_target_properties(Qt5::QuickTest PROPERTIES
                            INTERFACE_LINK_LIBRARIES "Qt5::Qml;Qt5::Test")
                    endif()
                    if(TARGET Qt5::QuickTest)
                        set(Qt5_QuickTest_FOUND TRUE)
                    endif()
                endif()
            endforeach()

            # 3) Versionless Qt::<Module> aliases: upstream links Qt::Core /
            #    Qt::Qml / Qt::Test / Qt::QuickTest (a real Qt5 install creates
            #    them; the CMakeDeps config only defines the Qt5:: names).
            foreach(_qt5_bridge_mod Core Gui Network Test Concurrent Xml Widgets
                                     PrintSupport DBus OpenGLExtensions Qml QuickTest)
                if(TARGET Qt5::${_qt5_bridge_mod} AND NOT TARGET Qt::${_qt5_bridge_mod})
                    add_library(Qt::${_qt5_bridge_mod} INTERFACE IMPORTED)
                    set_target_properties(Qt::${_qt5_bridge_mod} PROPERTIES
                        INTERFACE_LINK_LIBRARIES Qt5::${_qt5_bridge_mod})
                endif()
            endforeach()
            """
        ).replace("@MOC@", moc.replace("\\", "/"))
        save(self, os.path.join(generators, "Qt5Config.cmake"), bridge)

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
        self._stage_qml_import_modules()
        self.run(
            "ctest --test-dir {} --output-on-failure --parallel 1".format(
                shlex.quote(self.build_folder)
            ),
            env="conanbuild",
            ignore_errors=False,
        )

    def _stage_qml_import_modules(self):
        """让上游 qmltest 能 import QtTest/QtQuick。

        Qt5 的 QML 引擎只读 QML2_IMPORT_PATH（不读 QML_IMPORT_PATH），而上游
        tests/CMakeLists.txt 的 set_tests_properties 把它固定为 ${CMAKE_BINARY_DIR}；
        qtdeclarative 的 QML 模块（Qt/QtQml/QtQuick/QtQuick.2/QtTest）位于另一个
        Conan 包内。这里把这些模块软链进构建树，使固定导入路径即可解析到它们
        （不修改上游文件，也不改动依赖包内容）。
        """
        package = self.dependencies["qt5-qtdeclarative"].package_folder
        qml_root = os.path.join(package, "qml")
        if not os.path.isdir(qml_root):
            self.output.warning("qt5-qtdeclarative ships no qml/ module directory")
            return
        os.makedirs(self.build_folder, exist_ok=True)
        for name in sorted(os.listdir(qml_root)):
            source = os.path.join(qml_root, name)
            destination = os.path.join(self.build_folder, name)
            if os.path.lexists(destination):
                continue
            if name == "QtTest" and os.path.isdir(source):
                self._stage_qt_test_module(
                    source, os.path.join(package, "src", "imports", "testlib"), destination
                )
                continue
            try:
                os.symlink(source, destination)
            except OSError as error:
                self.output.warning(f"could not stage QML module {name}: {error}")

    def _stage_qt_test_module(self, qml_qt_test, testlib_src, destination):
        """拼出完整的 QtTest QML 模块。

        qt5-qtdeclarative 只把 libqmltestplugin.so 与 qmldir 装进了 qml/QtTest，
        缺 TestCase.qml / SignalSpy.qml / testlogger.js / plugins.qmltypes ——
        这些文件就在同一个包内（src/imports/testlib/，上游 install 未搬运）。
        这里以软链把两处内容合并成模块目录。
        """
        os.makedirs(destination, exist_ok=True)
        for root in (qml_qt_test, testlib_src):
            if not os.path.isdir(root):
                continue
            for name in sorted(os.listdir(root)):
                link = os.path.join(destination, name)
                source = os.path.join(root, name)
                if os.path.lexists(link) or not os.path.isfile(source):
                    continue
                try:
                    os.symlink(source, link)
                except OSError as error:
                    self.output.warning(f"could not stage QtTest file {name}: {error}")

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
        # Qt5 下上游库名不含版本后缀（Qt6 变体是 libgsettings-qt6）。
        self.cpp_info.libs = ["gsettings-qt"]
        # 头文件安装到 <prefix>/include/<arch>/qt5/QGSettings（上游用
        # CMAKE_INSTALL_FULL_INCLUDEDIR + CMAKE_LIBRARY_ARCHITECTURE）。
        self.cpp_info.includedirs = [self._qt_include_dir()]
        self.cpp_info.requires = [
            "qt5-qtbase::Qt5Core",
            "qt5-qtdeclarative::qt5-qtdeclarative",
            "glib::gio-2.0",
        ]
        self.cpp_info.set_property("pkg_config_name", "gsettings-qt")

    def _qt_include_dir(self):
        # 上游把 qgsettings.h 与转发头文件 QGSettings 一并装到
        # <prefix>/include/<triplet>/qt5/QGSettings/，且 .pc 的 Cflags 也指向
        # 该目录：消费方写 #include <QGSettings>，故 include 目录是该 QGSettings
        # 目录本身。
        for root, _, files in os.walk(os.path.join(self.package_folder, "include")):
            if "qgsettings.h" in files:
                return os.path.relpath(root, self.package_folder)
        return "include"
