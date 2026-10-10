#!/usr/bin/env python3
"""Conan recipe for qt5-qtquickcontrols2 5.15.19 on OpenHarmony PC.

QtQuickControls2 provides the Qt Quick Controls 2 module: the C++
libraries QtQuickTemplates2/QtQuickControls2 plus the QML style
plugins (Default/Fusion/Imagine/Material/Universal, Calendar,
Templates, Labs Platform). kirigami2's libkirigami hard-depends on
Qt5::QuickControls2, so this package unlocks the KDE Kirigami
ecosystem on HarmonyOS.
"""
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class Qt5QtQuickControls2Conan(ConanFile):
    name = "qt5-qtquickcontrols2"
    version = "5.15.19"
    description = "Qt5 Quick Controls 2 module (C++ libs + QML style plugins) for OpenHarmony"
    license = "LGPL-3.0"
    homepage = "https://www.qt.io/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qmake 工具与 Qt5 基础库由 qt5-qtbase 提供；
        # QtQuick/Qml 私有头由 qt5-qtdeclarative 提供
        self.requires("qt5-qtbase/5.15.2.2")
        self.requires("qt5-qtdeclarative/5.15.2")

    def layout(self):
        basic_layout(self)

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

    def _fix_qtbase_paths(self, qtbase_pkg):
        """Fix qt5-qtbase package's qt.conf and .pri files to use the package
        directory instead of the original build directory (relocatability)."""
        # Fix qt.conf
        qt_conf = os.path.join(qtbase_pkg, "bin", "qt.conf")
        if os.path.isfile(qt_conf):
            with open(qt_conf, "w", encoding="utf-8") as f:
                f.write(
                    "[EffectivePaths]\n"
                    "Prefix=..\n"
                    f"[DevicePaths]\n"
                    f"Prefix={qtbase_pkg}\n"
                    f"[Paths]\n"
                    f"Prefix={qtbase_pkg}\n"
                    f"HostPrefix={qtbase_pkg}\n"
                    "Sysroot=\n"
                    "SysrootifyPrefix=false\n"
                    "TargetSpec=linux-clang\n"
                    "HostSpec=linux-clang\n"
                )

        # Fix .pri files that reference the build directory
        build_dir_pattern = re.compile(
            r"(/[^\s]*/\.conan2/p/b/qt5-q[0-9a-f]+/b)"
        )
        for modules_dir_name in ("modules", "modules-inst"):
            modules_dir = os.path.join(qtbase_pkg, "mkspecs", modules_dir_name)
            if not os.path.isdir(modules_dir):
                continue
            for pri_file in os.listdir(modules_dir):
                if not pri_file.endswith(".pri"):
                    continue
                pri_path = os.path.join(modules_dir, pri_file)
                with open(pri_path, "r", encoding="utf-8") as f:
                    content = f.read()
                fixed_content = build_dir_pattern.sub(qtbase_pkg, content)
                if fixed_content != content:
                    with open(pri_path, "w", encoding="utf-8") as f:
                        f.write(fixed_content)

    def _fix_qtdecl_paths(self, qtdecl_pkg, qtbase_pkg):
        """Fix qt5-qtdeclarative .pri files to reference the correct
        package directories instead of the original build directory,
        and merge them into qt5-qtbase's mkspecs/modules."""
        # Pattern matches both .conan2 and .cache/conan2 build paths
        build_dir_pattern = re.compile(
            r"/[^\s]*/p/b/qt5-q[0-9a-f]+/b"
        )

        qtbase_modules = os.path.join(qtbase_pkg, "mkspecs", "modules")
        qtbase_modules_inst = os.path.join(qtbase_pkg, "mkspecs", "modules-inst")

        for modules_dir_name in ("modules", "modules-inst"):
            src_dir = os.path.join(qtdecl_pkg, "mkspecs", modules_dir_name)
            if not os.path.isdir(src_dir):
                continue
            for pri_file in os.listdir(src_dir):
                if not pri_file.endswith(".pri"):
                    continue
                src_path = os.path.join(src_dir, pri_file)
                with open(src_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # Fix build dir references to qtdeclarative package
                fixed_content = build_dir_pattern.sub(qtdecl_pkg, content)
                # Write to qt5-qtbase's mkspecs directory
                dst_dir = qtbase_modules if modules_dir_name == "modules" else qtbase_modules_inst
                os.makedirs(dst_dir, exist_ok=True)
                dst_path = os.path.join(dst_dir, pri_file)
                with open(dst_path, "w", encoding="utf-8") as f:
                    f.write(fixed_content)

    def _sync_forward_headers(self, src):
        """Replace syncqt forward headers with copies of the real headers.

        The qmake build's include/QtQuickControls2 and include/QtQuickTemplates2
        contain syncqt-generated forwarding headers that reference the source
        tree via relative paths like "../../src/quickcontrols2/qquickstyle.h".
        Those relative paths break once the package is relocated, so we copy
        the real headers from src/ over the forwarding stubs."""
        import shutil

        for module, src_subdir in (
            ("QtQuickControls2", "quickcontrols2"),
            ("QtQuickTemplates2", "quicktemplates2"),
        ):
            include_dir = os.path.join(src, "include", module)
            module_src = os.path.join(src, "src", src_subdir)
            if not os.path.isdir(include_dir) or not os.path.isdir(module_src):
                continue
            # Public forwarding headers: <module>/<name>.h -> src/<subdir>/<name>.h
            for entry in os.listdir(include_dir):
                real = os.path.join(module_src, entry)
                dst = os.path.join(include_dir, entry)
                if entry.endswith(".h") and os.path.isfile(real):
                    shutil.copyfile(real, dst)
            # Private versioned forwarding headers:
            # <module>/5.15.19/<module>/private/<name>_p.h -> src/<subdir>/<name>_p.h
            version_dir = os.path.join(include_dir, self.version)
            if not os.path.isdir(version_dir):
                continue
            for root, _dirs, files in os.walk(version_dir):
                for entry in files:
                    if not entry.endswith(".h"):
                        continue
                    real = os.path.join(module_src, entry)
                    dst = os.path.join(root, entry)
                    if os.path.isfile(real):
                        shutil.copyfile(real, dst)

    def _rewrite_ln_aliases(self, src):
        """Rewrite the qmake-generated `ln -s` ABI-alias steps to real copies.

        OpenHarmony workspaces forbid symlink creation (ln -s fails with
        EPERM) and also refuse to execute scripts created inside the build
        workspace (make reports "ln: Permission denied" for a PATH shim), so
        the aliases must be produced by a plain file copy.  qmake writes the
        alias steps with a leading `-`, hence the failures are silently
        ignored and the unversioned .so names never appear; libraries linked
        later in the same tree (libQt5QuickControls2 against
        libQt5QuickTemplates2) then fail with clang "no such file or
        directory".  The calling build() pre-generates the library
        subdirectory Makefiles with standalone qmake runs beforehand."""
        for root, _dirs, files in os.walk(src):
            for name in files:
                if name != "Makefile":
                    continue
                path = os.path.join(root, name)
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    content = handle.read()
                rewritten = content.replace(
                    "-ln -s $(TARGET)", "-cp -f $(TARGET)"
                ).replace(
                    "-$(QMAKE_LN_SHLIB) $(TARGET)", "-cp -f $(TARGET)"
                )
                if rewritten != content:
                    with open(path, "w", encoding="utf-8") as handle:
                        handle.write(rewritten)
                    # 保持比 .pro 更新，避免 make 重新生成 Makefile 而丢失改写
                    os.utime(path)

    def build(self):
        apply_conandata_patches(self)
        qtbase = self.dependencies["qt5-qtbase"]
        qtdecl = self.dependencies["qt5-qtdeclarative"]
        self._fix_qtbase_paths(qtbase.package_folder)
        qmake = os.path.join(qtbase.package_folder, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanException(
                "qt5-qtbase does not provide the required bin/qmake tool"
            )

        # Merge qt5-qtdeclarative .pri files into qt5-qtbase mkspecs so that
        # qtHaveModule(quick)/QT += quick resolves during qmake configure.
        self._fix_qtdecl_paths(qtdecl.package_folder, qtbase.package_folder)

        build_env = Environment()
        build_env.define("QTDIR", qtbase.package_folder)
        build_env.prepend_path("PATH", os.path.join(qtbase.package_folder, "bin"))
        build_env.append("LD_LIBRARY_PATH", os.path.join(qtbase.package_folder, "lib"))
        build_env.append("LD_LIBRARY_PATH", os.path.join(qtdecl.package_folder, "lib"))

        with build_env.vars(self).apply():
            # 顶层 qmake：生成顶层 Makefile 并运行模块 configure（写入
            # .qmake.cache、Styles 特性等）。不要用 `qmake -r` 一次性递归：
            # 同进程递归到 src/imports/controls 会丢失 configure 特性上下文，
            # 报 "Could not find feature quickcontrols2-default"。
            self.run(
                f'cd "{self.source_folder}" && '
                f'{shlex.quote(qmake)} -spec linux-clang qtquickcontrols2.pro'
            )
            # 两个库子目录的 Makefile 用独立 qmake 进程按 make 同款命令
            # 预生成，随后由 _rewrite_ln_aliases 把其中的 `ln -s` ABI 别名
            # 步骤改写为 cp 实拷贝（OHOS 工作区禁止创建符号链接（EPERM），
            # 且带 `-` 前缀的失败步骤会被 make 静默忽略，导致后续同树链接
            # 找不到无版本名 .so）。顶层 Makefile 对子 Makefile 采用
            # `test -e Makefile || $(QMAKE) ...` 判据，已存在者不会重新
            # 生成，改写内容得以保留。
            for subdir, pro_name in (
                ("src/quicktemplates2", "quicktemplates2.pro"),
                ("src/quickcontrols2", "quickcontrols2.pro"),
            ):
                sub_dir = f"{self.source_folder}/{subdir}"
                self.run(
                    f'cd "{sub_dir}" && {shlex.quote(qmake)} '
                    f'-o Makefile "{sub_dir}/{pro_name}" -spec linux-clang'
                )
            self._rewrite_ln_aliases(self.source_folder)
            jobs = self.conf.get("tools.build:jobs", default=4, check_type=int)
            self.run(f'cd "{self.source_folder}" && make -j{jobs} QMAKE_STRIP=""')

        # Make include/ relocatable before packaging
        self._sync_forward_headers(self.source_folder)

    def package(self):
        src = self.source_folder

        # Copy QML plugins (the main build product): qml/QtQuick/Controls.2,
        # qml/Qt/labs/calendar, qml/Qt/labs/platform, qml/QtQuick/Templates.2
        qml_dir = os.path.join(src, "qml")
        if os.path.isdir(qml_dir):
            copy(self, "*", src=qml_dir,
                 dst=os.path.join(self.package_folder, "qml"), keep_path=True)

        # Copy C++ libraries (QtQuickTemplates2, QtQuickControls2)
        lib_dir = os.path.join(src, "lib")
        if os.path.isdir(lib_dir):
            copy(self, "*.so*", src=lib_dir,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
            copy(self, "*.prl", src=lib_dir,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)

        # Copy headers (include/QtQuickControls2, include/QtQuickTemplates2)
        if os.path.isdir(os.path.join(src, "include")):
            copy(self, "*", src=os.path.join(src, "include"),
                 dst=os.path.join(self.package_folder, "include"), keep_path=True)

        # Copy mkspecs modules (qt_lib_quickcontrols2.pri etc.)
        mkspecs_dir = os.path.join(src, "mkspecs")
        if os.path.isdir(mkspecs_dir):
            copy(self, "*", src=mkspecs_dir,
                 dst=os.path.join(self.package_folder, "mkspecs"), keep_path=True)

        # Copy cmake configs (Qt5QuickControls2 config files for find_package)
        cmake_dir = os.path.join(lib_dir, "cmake") if os.path.isdir(lib_dir) else None
        if cmake_dir and os.path.isdir(cmake_dir):
            copy(self, "*", src=cmake_dir,
                 dst=os.path.join(self.package_folder, "lib", "cmake"), keep_path=True)

        # Copy plugins if any
        plugins_dir = os.path.join(src, "plugins")
        if os.path.isdir(plugins_dir):
            copy(self, "*", src=plugins_dir,
                 dst=os.path.join(self.package_folder, "plugins"), keep_path=True)

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["Qt5QuickControls2", "Qt5QuickTemplates2"]
        # QQuickStyle API 等公共头位于 include/QtQuickControls2；
        # 私有头位于 include/QtQuickControls2/5.15.19/... 与 QtQuickTemplates2
        self.cpp_info.includedirs = [
            "include",
            "include/QtQuickControls2",
            "include/QtQuickTemplates2",
            "include/QtQuickControls2/5.15.19",
            "include/QtQuickControls2/5.15.19/QtQuickControls2",
            "include/QtQuickTemplates2/5.15.19",
            "include/QtQuickTemplates2/5.15.19/QtQuickTemplates2",
        ]
        self.cpp_info.requires = [
            "qt5-qtbase::Qt5Core",
            "qt5-qtbase::Qt5Gui",
            "qt5-qtdeclarative::qt5-qtdeclarative",
        ]
        self.cpp_info.set_property("cmake_file_name", "Qt5QuickControls2")
        self.cpp_info.set_property("cmake_target_name", "Qt5::QuickControls2")
