#!/usr/bin/env python3
"""Conan recipe for qt5-qtsensors 5.15.2 on OpenHarmony PC.

QtSensors provides the Qt5 Sensors module: the QtSensors C++ library,
sensor backend plugins, sensorgesture plugins and the QtSensors QML
import module.  Built with qmake from the qt5-qtbase package following
the established qt5-qtmultimedia pattern: a private writable Qt prefix
mirrors qtbase (symlinks + rewritten mkspecs), qmake builds from it,
and `make install` stages into an INSTALL_ROOT inside the build folder
before relocation into the package.

OHOS platform adaptation:
  * SENSORS_PLUGINS=generic — only the pure-software generic backend
    plugin is built.  The upstream default linux set would also build
    the linuxsys backend (reads /dev/input, absent on OHOS PC) and the
    iio-sensor-proxy backend (requires a system D-Bus daemon; loading
    it on OHOS segfaults inside QDBusConnection::systemBus()).
  * The QML import module (src/imports) links Qt5Qml/Qt5Quick from
    qt5-qtdeclarative; its module .pri files are merged into the
    private Qt prefix (qt5-qtgraphicaleffects pattern).
  * All shipped .so files are signed with binary-sign-tool.
"""
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    get, apply_conandata_patches, export_conandata_patches,
)
from conan.tools.layout import basic_layout


class Qt5QtsensorsConan(ConanFile):
    name = "qt5-qtsensors"
    version = "5.15.2"
    description = "Qt5 Sensors module (QtSensors library, sensor/gesture plugins, QML module) for OpenHarmony"
    license = "LGPL-3.0"
    homepage = "https://www.qt.io/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    # 同时匹配 .conan2 与 .cache/conan2 构建缓存路径（qt5-qtmultimedia 模式）
    _BUILD_DIR_PATTERN = re.compile(
        r"(/[^\s]*/(?:\.cache/)?\.?conan2/p/b/qt5-q[0-9a-f]+/b)"
    )

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qmake 工具与 Qt5 基础库由 qt5-qtbase 提供
        self.requires("qt5-qtbase/5.15.2.2")
        # QtSensors QML 模块（src/imports）链接 Qt5Qml/Qt5Quick，
        # 由 qt5-qtdeclarative 提供（参照 qt5-qtgraphicaleffects 先例）
        self.requires("qt5-qtdeclarative/5.15.2")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        source_data = self.conan_data["sources"][self.version]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get(self, url=url, sha256=source_data.get("sha256", ""), strip_root=True)
                return
            except ConanException as error:
                self.output.warning(f"Failed to download source from {url}: {error}")
        raise ConanInvalidConfiguration("Unable to download source from all mirrors")

    # ------------------------------------------------------------------
    # 私有可写 Qt prefix（qt5-qtmultimedia 模式）
    # ------------------------------------------------------------------

    def _rewrite_module_files(self, mkspecs_dir, target_pkg_dir):
        build_dir_pattern = self._BUILD_DIR_PATTERN
        for modules_dir_name in ("modules", "modules-inst"):
            modules_dir = os.path.join(mkspecs_dir, modules_dir_name)
            if not os.path.isdir(modules_dir):
                continue
            for pri_file in os.listdir(modules_dir):
                if not pri_file.endswith(".pri"):
                    continue
                pri_path = os.path.join(modules_dir, pri_file)
                with open(pri_path, "r", encoding="utf-8") as f:
                    content = f.read()
                fixed = build_dir_pattern.sub(target_pkg_dir, content)
                if fixed != content:
                    with open(pri_path, "w", encoding="utf-8") as f:
                        f.write(fixed)

    def _merge_qtdecl_modules(self, qt_root, qtdecl_pkg):
        """将 qt5-qtdeclarative 的模块 .pri（重写为指向其包目录）与
        mkspecs/features 合并进私有 Qt prefix，使 `QT += qml quick`
        可解析（qt5-qtgraphicaleffects 模式，但不改动共享缓存包）。"""
        pattern = self._BUILD_DIR_PATTERN
        for modules_dir_name in ("modules", "modules-inst"):
            src_dir = os.path.join(qtdecl_pkg, "mkspecs", modules_dir_name)
            if not os.path.isdir(src_dir):
                continue
            dst_dir = os.path.join(qt_root, "mkspecs", modules_dir_name)
            os.makedirs(dst_dir, exist_ok=True)
            for pri_file in os.listdir(src_dir):
                if not pri_file.endswith(".pri"):
                    continue
                src_path = os.path.join(src_dir, pri_file)
                with open(src_path, "r", encoding="utf-8") as f:
                    content = f.read()
                fixed = pattern.sub(qtdecl_pkg, content)
                with open(os.path.join(dst_dir, pri_file), "w", encoding="utf-8") as f:
                    f.write(fixed)
        features_src = os.path.join(qtdecl_pkg, "mkspecs", "features")
        features_dst = os.path.join(qt_root, "mkspecs", "features")
        if os.path.isdir(features_src):
            os.makedirs(features_dst, exist_ok=True)
            for prf in os.listdir(features_src):
                src_path = os.path.join(features_src, prf)
                if os.path.isfile(src_path):
                    shutil.copy2(src_path, os.path.join(features_dst, prf))

    def _build_qt_tree(self, qtbase_pkg, qtdecl_pkg):
        qt_root = os.path.join(self.build_folder, "qt-prefix")
        if os.path.isdir(qt_root):
            shutil.rmtree(qt_root)
        os.makedirs(qt_root)
        # 顶层条目符号链接（bin/mkspecs 单独处理）
        for entry in os.listdir(qtbase_pkg):
            if entry in ("bin", "mkspecs"):
                continue
            os.symlink(os.path.join(qtbase_pkg, entry), os.path.join(qt_root, entry))
        bin_src = os.path.join(qtbase_pkg, "bin")
        bin_dst = os.path.join(qt_root, "bin")
        os.makedirs(bin_dst)
        for entry in os.listdir(bin_src):
            if entry == "qt.conf":
                continue
            os.symlink(os.path.join(bin_src, entry), os.path.join(bin_dst, entry))
        with open(os.path.join(bin_dst, "qt.conf"), "w", encoding="utf-8") as f:
            f.write(
                "[EffectivePaths]\n"
                "Prefix=..\n"
                "[DevicePaths]\n"
                f"Prefix={qt_root}\n"
                "[Paths]\n"
                f"Prefix={qt_root}\n"
                f"HostPrefix={qt_root}\n"
                "Sysroot=\n"
                "SysrootifyPrefix=false\n"
                "TargetSpec=linux-clang\n"
                "HostSpec=linux-clang\n"
            )
        mkspecs_dst = os.path.join(qt_root, "mkspecs")
        shutil.copytree(os.path.join(qtbase_pkg, "mkspecs"), mkspecs_dst, symlinks=True)
        # qtbase 构建缓存路径 → qtbase 包目录
        self._rewrite_module_files(mkspecs_dst, qtbase_pkg)
        # 合并 qtdeclarative 模块 pri 与 features（qml/quick 模块解析）
        self._merge_qtdecl_modules(qt_root, qtdecl_pkg)
        return qt_root

    def _qmake_env(self, qt_root, qtbase_pkg, qtdecl_pkg):
        build_env = Environment()
        build_env.define("QTDIR", qt_root)
        build_env.prepend_path("PATH", os.path.join(qt_root, "bin"))
        build_env.append("LD_LIBRARY_PATH", os.path.join(qtbase_pkg, "lib"))
        build_env.append("LD_LIBRARY_PATH", os.path.join(qtdecl_pkg, "lib"))
        return build_env

    # ------------------------------------------------------------------
    # 构建
    # ------------------------------------------------------------------

    def build(self):
        apply_conandata_patches(self)
        qtbase = self.dependencies["qt5-qtbase"]
        qtdecl = self.dependencies["qt5-qtdeclarative"]
        qt_root = self._build_qt_tree(qtbase.package_folder, qtdecl.package_folder)
        qmake = os.path.join(qt_root, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanException("qt5-qtbase does not provide bin/qmake")
        build_env = self._qmake_env(qt_root, qtbase.package_folder, qtdecl.package_folder)
        with build_env.vars(self).apply():
            # SENSORS_PLUGINS=generic：OHOS 无 /dev/input 传感器节点与系统
            # D-Bus 守护进程，上游 linux/iio-sensor-proxy 硬件后端不可用
            # （iio 插件加载即 QDBusConnection::systemBus() 空指针崩溃），
            # 仅构建 generic 纯软件后端（上游官方 qmake 开关，无需补丁）
            self.run(
                f'cd "{self.source_folder}" && {shlex.quote(qmake)} -spec linux-clang '
                f'SENSORS_PLUGINS=generic qtsensors.pro'
            )
            jobs = self.conf.get("tools.build:jobs", default=2, check_type=int)
            # QMAKE_STRIP=""：OHOS 加载器拒绝 strip 过的 ELF；
            # install 阶段用 STRIP=true 跳过 strip --strip-unneeded
            self.run(f'cd "{self.source_folder}" && make -j{jobs} QMAKE_STRIP=""')

    # ------------------------------------------------------------------
    # 打包
    # ------------------------------------------------------------------

    def package(self):
        qtbase_pkg = self.dependencies["qt5-qtbase"].package_folder
        qtdecl_pkg = self.dependencies["qt5-qtdeclarative"].package_folder
        install_root = os.path.join(self.build_folder, "__install_root")
        if os.path.isdir(install_root):
            shutil.rmtree(install_root)
        os.makedirs(install_root)
        qt_root = os.path.join(self.build_folder, "qt-prefix")
        if not os.path.isdir(qt_root):
            qt_root = self._build_qt_tree(qtbase_pkg, qtdecl_pkg)
        build_env = self._qmake_env(qt_root, qtbase_pkg, qtdecl_pkg)
        with build_env.vars(self).apply():
            self.run(
                f'cd "{self.source_folder}" && make install '
                f'INSTALL_ROOT={shlex.quote(install_root)} STRIP=true'
            )
        staged = os.path.join(install_root, qt_root.lstrip(os.sep))
        if not os.path.isdir(staged):
            raise ConanException(
                f"make install did not stage anything under {staged}"
            )
        moved = []
        for sub in ("lib", "include", "mkspecs", "plugins", "bin", "qml"):
            src_dir = os.path.join(staged, sub)
            if not os.path.isdir(src_dir):
                continue
            shutil.copytree(src_dir, os.path.join(self.package_folder, sub),
                            symlinks=True, dirs_exist_ok=True)
            moved.append(sub)
        if "lib" not in moved:
            raise ConanException(f"incomplete Qt prefix (got: {moved})")
        shutil.rmtree(install_root, ignore_errors=True)

        # 重写打包后 .prl/.la/.pc 中残留的 build-dir/source-dir 路径
        qt_prefix_dir = os.path.join(self.build_folder, "qt-prefix")
        own_build_dir = self.build_folder.rstrip(os.sep)
        build_root = os.path.dirname(own_build_dir)
        source_dir = self.source_folder.rstrip(os.sep)
        for root, _dirs, files in os.walk(self.package_folder):
            for name in files:
                path = os.path.join(root, name)
                if not name.endswith((".prl", ".la", ".pc")):
                    continue
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                except (UnicodeDecodeError, OSError):
                    continue
                original = content
                for stale in sorted(
                    {qt_prefix_dir, own_build_dir, source_dir, build_root}, key=len, reverse=True
                ):
                    content = content.replace(stale, self.package_folder)
                if content != original:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(content)

        # OHOS：对包内全部 .so 签名（qrencode 模式）
        if self.settings.os == "OHOS":
            self._sign_shared_objects()

    def _sign_shared_objects(self):
        """用目标机原生签名工具对 OHOS ELF 共享对象签名。"""
        objcopy = os.environ.get("OHOS_LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("OHOS_BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        for root, _dirs, files in os.walk(self.package_folder):
            for name in files:
                if not (name.endswith(".so") or ".so." in name):
                    continue
                path = os.path.join(root, name)
                if os.path.islink(path):
                    continue
                self.run('{0} --remove-section .codesign "{1}" 2>/dev/null || true'.format(objcopy, path))
                self.run('{0} sign -inFile "{1}" -outFile "{1}" -selfSign 1'.format(signer, path))

    # ------------------------------------------------------------------
    # 包信息
    # ------------------------------------------------------------------

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = ["Qt5Sensors"]
        self.cpp_info.includedirs = ["include", "include/QtSensors"]
        self.cpp_info.requires = [
            "qt5-qtbase::Qt5Core",
            "qt5-qtdeclarative::qt5-qtdeclarative",
        ]
        self.cpp_info.set_property("cmake_file_name", "Qt5Sensors")
        self.cpp_info.set_property("cmake_target_name", "Qt5::Sensors")
