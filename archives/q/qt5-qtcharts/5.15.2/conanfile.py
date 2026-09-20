#!/usr/bin/env python3
"""Conan recipe for qt5-qtcharts 5.15.2 on OpenHarmony PC.

Qt Charts is a Qt5 module providing chart widgets (QChart/QChartView and
related series/axis classes) and a QML plugin (QtCharts module) backed by
libQt5Charts and libqtchartsqml2. It is built with qmake from the
qt5-qtbase package and depends on qt5-qtbase (Core/Gui/Widgets) and
qt5-qtdeclarative (Qml/Quick, required by the chartsqml2 plugin).
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


class Qt5QtchartsConan(ConanFile):
    name = "qt5-qtcharts"
    version = "5.15.2"
    description = "Qt5 Charts module (QChart/QChartView + QtCharts QML plugin) for OpenHarmony"
    license = "LGPL-3.0"
    homepage = "https://www.qt.io/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    # Matches both the `.conan2/p/b/<pkg>/b` and the `.cache/conan2/p/b/<pkg>/b`
    # conan build-dir layouts (both shapes appear across cache versions/paths).
    # Shared by _rewrite_module_files() and _build_qt_tree() so the two never
    # diverge: a too-narrow pattern (matching only `.conan2`) leaves stale
    # `.cache/conan2` build-dir paths in the merged qtdeclarative .pri files,
    # which makes qmake fail to load QtQml/QtQuick and silently drop the
    # chartsqml2 QML plugin subdirectory.
    _BUILD_DIR_PATTERN = re.compile(
        r"(/[^\s]*/(?:\.cache/)?\.?conan2/p/b/qt5-q[0-9a-f]+/b)"
    )

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # No patches are shipped with this recipe (manifest.yaml: patches: none),
        # so this is a deliberate no-op kept for the standard recipe shape: if a
        # genuine upstream patch is ever added to conandata.yml it is exported
        # automatically. See notes.md for why the 8 previously-archived
        # "patches" were removed (they were qmake build artifacts, not source
        # changes, and never participated in the build).
        export_conandata_patches(self)

    def requirements(self):
        # qmake 工具与 Qt5 Core/Gui/Widgets 基础库由 qt5-qtbase 提供；
        # Qt5Qml/Qt5Quick 由 qt5-qtdeclarative 提供（chartsqml2 QML 插件需要）。
        # 注意: qt5-qtdeclarative/5.15.2 的依赖是 qt5-qtbase/5.15.2.2，
        # 必须一致以避免版本冲突（qt5-qtbase/5.15.2 会与 5.15.2.2 冲突）。
        self.requires("qt5-qtbase/5.15.2.2")
        self.requires("qt5-qtdeclarative/5.15.2")

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
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

    def _rewrite_module_files(self, mkspecs_dir, target_pkg_dir):
        """Rewrite module .pri files under `mkspecs_dir` that still reference a
        Qt build directory, pointing them at `target_pkg_dir`.

        `mkspecs_dir` is our own writable copy; `target_pkg_dir` is the real
        package whose libs/headers the .pri entries should resolve to.
        """
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
                fixed_content = build_dir_pattern.sub(target_pkg_dir, content)
                if fixed_content != content:
                    with open(pri_path, "w", encoding="utf-8") as f:
                        f.write(fixed_content)

    def _build_qt_tree(self, qtbase_pkg, qtdeclarative_pkg):
        """Build a private, writable Qt "prefix" inside our own build folder.

        qmake insists on discovering mkspecs/modules under $QTDIR, and the
        qtdeclarative module .pri files must sit next to qtbase's so that
        qtHaveModule(quick) becomes true and the chartsqml2 plugin is built.

        The obvious shortcut -- writing qt.conf and copying the .pri files
        straight into the qt5-qtbase package -- mutates a *dependency* package
        in the shared Conan cache. That corrupts it for every other consumer:
        the rewritten qt.conf Prefix and the injected qt_lib_qml.pri outlive
        our build, and a later build whose qtbase build dir has been pruned
        then fails with `Unknown module(s) in QT: core gui testlib widgets`.

        So instead we mirror qtbase into build_folder/qt-prefix using symlinks
        for the bulk payload (bin/lib/plugins/qml/...) and *real copies* only
        for the two trees we must rewrite (bin/qt.conf and mkspecs/). The
        dependency packages stay byte-for-byte untouched.
        """
        qt_root = os.path.join(self.build_folder, "qt-prefix")
        if os.path.isdir(qt_root):
            shutil.rmtree(qt_root)
        os.makedirs(qt_root)

        # Symlink every top-level entry of qtbase except the ones we rewrite.
        for entry in os.listdir(qtbase_pkg):
            if entry in ("bin", "mkspecs"):
                continue
            os.symlink(os.path.join(qtbase_pkg, entry), os.path.join(qt_root, entry))

        # bin/: symlink the executables, but write our own qt.conf.
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

        # mkspecs/: real copy, then rewrite stale build-dir paths and merge in
        # qtdeclarative's module definitions.
        mkspecs_dst = os.path.join(qt_root, "mkspecs")
        shutil.copytree(os.path.join(qtbase_pkg, "mkspecs"), mkspecs_dst, symlinks=True)

        # qtbase's own .pri files still reference qtbase's build dir; point them
        # at the real qtbase package (its libs/headers genuinely live there).
        self._rewrite_module_files(mkspecs_dst, qtbase_pkg)

        # Merge qtdeclarative's module .pri files in. Their paths must be
        # rewritten to the installed qtdeclarative package: the pattern has to
        # cover BOTH the `.conan2` and `.cache/conan2` shapes, since the old
        # narrow pattern left `.cache/conan2` paths stale, qmake then could not
        # read the QtQml/QtQuick .pri files, and chartsqml2 was silently skipped.
        for modules_dir_name in ("modules", "modules-inst"):
            src_dir = os.path.join(qtdeclarative_pkg, "mkspecs", modules_dir_name)
            if not os.path.isdir(src_dir):
                continue
            dst_dir = os.path.join(mkspecs_dst, modules_dir_name)
            os.makedirs(dst_dir, exist_ok=True)
            for pri_file in os.listdir(src_dir):
                if not pri_file.endswith(".pri"):
                    continue
                with open(os.path.join(src_dir, pri_file), "r", encoding="utf-8") as f:
                    content = f.read()
                content = self._BUILD_DIR_PATTERN.sub(qtdeclarative_pkg, content)
                with open(os.path.join(dst_dir, pri_file), "w", encoding="utf-8") as f:
                    f.write(content)

        return qt_root

    def _qmake_env(self, qt_root, qtbase_pkg, qtdeclarative_pkg):
        """Environment shared by the qmake/make/make-install invocations.

        QTDIR/PATH point at our private qt-prefix mirror (see _build_qt_tree),
        never at the dependency package itself.
        """
        build_env = Environment()
        build_env.define("QTDIR", qt_root)
        build_env.prepend_path("PATH", os.path.join(qt_root, "bin"))
        build_env.append("LD_LIBRARY_PATH", os.path.join(qtbase_pkg, "lib"))
        build_env.append("LD_LIBRARY_PATH", os.path.join(qtdeclarative_pkg, "lib"))
        return build_env

    def build(self):
        # No-op unless conandata.yml declares patches (it currently declares
        # none) — kept so a future genuine upstream patch is applied here.
        apply_conandata_patches(self)
        qtbase = self.dependencies["qt5-qtbase"]
        qtdeclarative = self.dependencies["qt5-qtdeclarative"]
        qt_root = self._build_qt_tree(
            qtbase.package_folder, qtdeclarative.package_folder
        )
        qmake = os.path.join(qt_root, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanException(
                "qt5-qtbase/5.15.2.2 does not provide the required bin/qmake tool"
            )
        build_env = self._qmake_env(
            qt_root, qtbase.package_folder, qtdeclarative.package_folder
        )
        with build_env.vars(self).apply():
            self.run(
                f'cd "{self.source_folder}" && {shlex.quote(qmake)} -spec linux-clang qtcharts.pro'
            )
            jobs = self.conf.get("tools.build:jobs", default=4, check_type=int)
            self.run(f'cd "{self.source_folder}" && make -j{jobs} QMAKE_STRIP=""')

    def package(self):
        # Use qmake's own `make install` instead of hand-copying the build tree.
        #
        # Why: the headers qmake leaves in the *build* tree's include/QtCharts/
        # are forwarding stubs (`#include "../../src/charts/qchart.h"`), and the
        # private ones under include/QtCharts/5.15.2/QtCharts/private/ point at
        # `../../../../../src/charts/*_p.h`. Shipping those stubs only works if
        # the whole 51MB qmake build tree (src/) is packaged too — which is what
        # the old recipe did. `make install` runs the syncqt-driven install rules
        # (install_gen_headers / install_targ_headers / install_private_headers),
        # which copy the *real* headers out of src/charts into
        # QT_INSTALL_HEADERS/QtCharts, and additionally installs the versioned
        # .so + symlinks, .prl/.la/Qt5Charts.pc, mkspecs/modules/*.pri, the
        # Qt5Charts cmake config and the qml/QtCharts plugin. Result: a
        # self-contained ~5MB package with no build tree.
        qtbase_pkg = self.dependencies["qt5-qtbase"].package_folder
        qtdeclarative_pkg = self.dependencies["qt5-qtdeclarative"].package_folder

        # Qt modules install into QT_INSTALL_PREFIX, which is now our private
        # qt-prefix mirror (see _build_qt_tree), so INSTALL_ROOT stages them
        # under <root>/<qt_root>. Resolve qt_root FIRST, then derive the staged
        # path from it — deriving it from qtbase_pkg was the bug that made this
        # check fail after the mirror was introduced.
        # /tmp is read-only on OHOS (E002) → stage inside the build folder.
        install_root = os.path.join(self.build_folder, "__install_root")
        if os.path.isdir(install_root):
            shutil.rmtree(install_root)
        os.makedirs(install_root)

        # `make install` re-runs qmake-generated rules, so it needs the same
        # private qt-prefix mirror build() used (never the dependency package).
        qt_root = os.path.join(self.build_folder, "qt-prefix")
        if not os.path.isdir(qt_root):
            qt_root = self._build_qt_tree(qtbase_pkg, qtdeclarative_pkg)

        build_env = self._qmake_env(qt_root, qtbase_pkg, qtdeclarative_pkg)
        with build_env.vars(self).apply():
            # STRIP=true neutralises the `strip --strip-unneeded` that qmake's
            # install_target rule applies to the installed .so. On OHOS that
            # strip silently corrupts the dynamic symbol table: the library still
            # lists the QtCharts symbols in .dynsym, but the loader refuses it
            # with "Error loading shared library libQt5Charts.so.5" and every
            # QtCharts symbol becomes "symbol not found" at relocation time.
            # Same reason build() passes QMAKE_STRIP="".
            self.run(
                f'cd "{self.source_folder}" && make install '
                f'INSTALL_ROOT={shlex.quote(install_root)} STRIP=true'
            )

        staged = os.path.join(install_root, qt_root.lstrip(os.sep))
        if not os.path.isdir(staged):
            raise ConanException(
                f"make install did not stage anything under {staged}; "
                f"INSTALL_ROOT contents: {os.listdir(install_root)}"
            )

        # Relocate the staged Qt prefix into the package folder. copytree with
        # symlinks=True keeps the libQt5Charts.so -> .so.5.15.2 SONAME chain.
        moved = []
        for sub in ("lib", "include", "qml", "mkspecs", "plugins", "bin"):
            src_dir = os.path.join(staged, sub)
            if not os.path.isdir(src_dir):
                continue
            shutil.copytree(src_dir, os.path.join(self.package_folder, sub),
                            symlinks=True, dirs_exist_ok=True)
            moved.append(sub)
        if "lib" not in moved or "include" not in moved:
            raise ConanException(
                f"make install produced an incomplete Qt prefix (got: {moved})"
            )
        shutil.rmtree(install_root, ignore_errors=True)

        # Qt5Charts.pc / libQt5Charts.la / libQt5Charts.prl record paths from the
        # build environment. Three distinct classes of stale path must be fixed,
        # and the ORDER matters:
        #
        #  1. the private qt-prefix mirror (build_folder/qt-prefix), which is
        #     where make install nominally staged us -> repoint at this package;
        #  2. any other reference to our own build folder -> this package;
        #  3. references to the *real* qtbase package must be LEFT ALONE:
        #     Qt5Core/Gui/Widgets genuinely live there, so the .prl's
        #     QMAKE_PRL_LIBS and the .pc's -L entries must keep pointing at
        #     qtbase. Rewriting those (as an earlier version did) produced a
        #     .prl claiming libQt5Core.so sits in the qtcharts package, which
        #     breaks every downstream qmake consumer.
        #
        # Because qt-prefix lives *inside* build_folder and symlinks to qtbase,
        # a blanket _BUILD_DIR_PATTERN.sub() would also rewrite class 3. So the
        # qt-prefix/own-build-folder replacements are applied explicitly and the
        # broad pattern is NOT used here.
        #
        # Note build_folder is <build-root>/build-release while qmake records
        # paths like <build-root>/src/charts in QMAKE_PRL_BUILD_DIR (the source
        # tree sits one level ABOVE build_folder), so the build ROOT has to be
        # scrubbed too — matching only build_folder leaves that line dangling.
        qt_prefix_dir = os.path.join(self.build_folder, "qt-prefix")
        own_build_dir = self.build_folder.rstrip(os.sep)
        build_root = os.path.dirname(own_build_dir)
        source_dir = self.source_folder.rstrip(os.sep)
        for rel_path in (
            os.path.join("lib", "pkgconfig", "Qt5Charts.pc"),
            os.path.join("lib", "libQt5Charts.la"),
            os.path.join("lib", "libQt5Charts.prl"),
        ):
            target = os.path.join(self.package_folder, rel_path)
            if not os.path.isfile(target):
                continue
            with open(target, "r", encoding="utf-8") as f:
                content = f.read()
            original = content
            # Longest paths first so nested prefixes are not partially rewritten.
            for stale in sorted(
                {qt_prefix_dir, own_build_dir, source_dir, build_root}, key=len, reverse=True
            ):
                content = content.replace(stale, self.package_folder)
            if content != original:
                with open(target, "w", encoding="utf-8") as f:
                    f.write(content)

        # Fail loudly rather than shipping a package that points at directories
        # which no longer exist once the build folder is pruned. Only our OWN
        # build tree is a defect; paths into the qtbase/qtdeclarative packages
        # are legitimate dependency references.
        leaked = []
        for root, _dirs, files in os.walk(self.package_folder):
            for name in files:
                path = os.path.join(root, name)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        text = f.read()
                except (UnicodeDecodeError, OSError):
                    continue
                if build_root in text:
                    leaked.append(os.path.relpath(path, self.package_folder))
        if leaked:
            raise ConanException(
                "package still references Qt build directories (pruned after "
                f"build): {sorted(leaked)}"
            )

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        # 主 C++ 库: libQt5Charts.so（链接 Qt5Core/Qt5Gui/Qt5Widgets）。
        # QML 插件 (qml/QtCharts/libqtchartsqml2.so) 由 qt5-qtdeclarative 的
        # Qt5Qml/Qt5Quick 支撑，声明在 requires 中以保持完整依赖链。
        self.cpp_info.libs = ["Qt5Charts"]
        self.cpp_info.includedirs = ["include", "include/QtCharts"]
        self.cpp_info.requires = [
            "qt5-qtbase::Qt5Core", "qt5-qtbase::Qt5Gui", "qt5-qtbase::Qt5Widgets",
            "qt5-qtdeclarative::qt5-qtdeclarative",
        ]
        self.cpp_info.set_property("cmake_file_name", "Qt5Charts")
        self.cpp_info.set_property("cmake_target_name", "Qt5::Charts")
