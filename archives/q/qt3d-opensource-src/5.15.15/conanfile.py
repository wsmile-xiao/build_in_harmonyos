#!/usr/bin/env python3
"""Conan recipe for qt3d-opensource-src 5.15.15 on OpenHarmony PC.

Qt3D provides C++ and QML APIs for 3D graphics, including rendering,
input, animation, and extras. It is built with qmake against qt5-qtbase
and qt5-qtdeclarative.

Historical adaptation (qt5-qt3d 5.15.2) noted: no source modifications
required; Qt3D bundles assimp internally for 3D model loading.
"""
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class Qt3dOpenSourceSrcConan(ConanFile):
    name = "qt3d-opensource-src"
    version = "5.15.15"
    description = "Qt5 3D module (Core, Render, Input, Logic, Animation, Extras, Quick) for OpenHarmony"
    license = "LGPL-3.0"
    homepage = "https://wiki.qt.io/Qt3D"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")
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
        sha256 = source_data.get("sha256", "")
        for url in urls:
            try:
                get(self, url=url, sha256=sha256, strip_root=True)
                return
            except ConanException as error:
                self.output.warning(f"Failed to download source from {url}: {error}")
        raise ConanInvalidConfiguration("Unable to download Qt3D source from all mirrors")

    def _fix_qtbase_paths(self, qtbase_pkg):
        """Fix qt5-qtbase package's qt.conf and .pri files to use the package
        directory instead of the original build directory (relocatability)."""
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

        # Also patch .prl files in lib/ directory (stale build paths in
        # QMAKE_PRL_LIBS cause linker errors for plugins that link against
        # Qt5 libraries via .prl references)
        lib_dir = os.path.join(qtbase_pkg, "lib")
        if os.path.isdir(lib_dir):
            for prl_file in os.listdir(lib_dir):
                if not prl_file.endswith(".prl"):
                    continue
                prl_path = os.path.join(lib_dir, prl_file)
                try:
                    with open(prl_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    fixed_content = build_dir_pattern.sub(qtbase_pkg, content)
                    if fixed_content != content:
                        with open(prl_path, "w", encoding="utf-8") as f:
                            f.write(fixed_content)
                except OSError as e:
                    self.output.warning(f"Could not patch {prl_path}: {e}")

    def _merge_qtdecl_mkspecs(self, qtdecl_pkg, qtbase_pkg):
        """Merge qt5-qtdeclarative's module .pri files into qtbase's
        mkspecs/modules(-inst) so qmake can resolve the qml/quick modules.

        Without this merge, qmake only sees qtbase's modules and silently
        skips every qtHaveModule(qml)/qtHaveModule(quick) guarded project,
        so none of the Qt53DQuick* libraries would be built.
        """
        # Matches stale build-dir paths in both ~/.conan2 and ~/.cache/conan2
        build_dir_pattern = re.compile(r"/[^\s]*/p/b/qt5-q[0-9a-f]+/b")
        for modules_dir_name in ("modules", "modules-inst"):
            src_dir = os.path.join(qtdecl_pkg, "mkspecs", modules_dir_name)
            if not os.path.isdir(src_dir):
                continue
            dst_dir = os.path.join(qtbase_pkg, "mkspecs", modules_dir_name)
            os.makedirs(dst_dir, exist_ok=True)
            for pri_file in os.listdir(src_dir):
                if not pri_file.endswith(".pri"):
                    continue
                src_path = os.path.join(src_dir, pri_file)
                with open(src_path, "r", encoding="utf-8") as f:
                    content = f.read()
                fixed_content = build_dir_pattern.sub(qtdecl_pkg, content)
                with open(os.path.join(dst_dir, pri_file), "w", encoding="utf-8") as f:
                    f.write(fixed_content)

    def _fix_makefile_paths(self, qtbase_pkg):
        """Fix stale Conan build directory paths in generated Makefiles.

        After qmake generates Makefiles, some may still reference the
        qtbase build directory instead of the package directory.
        This walks all generated Makefiles and replaces stale paths.
        """
        import glob
        build_dir_pattern = re.compile(
            r"(/[^\s]*/\.conan2/p/b/qt5-q[0-9a-f]+/b)"
        )
        # Walk source tree for Makefiles
        for root, dirs, files in os.walk(self.source_folder):
            for fname in files:
                if fname == "Makefile" or fname.startswith("Makefile.") or fname.endswith(".prl") or fname.endswith(".pri") or fname.endswith(".la"):
                    fpath = os.path.join(root, fname)
                    if not os.path.isfile(fpath):
                        continue
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        fixed = build_dir_pattern.sub(qtbase_pkg, content)
                        if fixed != content:
                            with open(fpath, "w", encoding="utf-8") as f:
                                f.write(fixed)
                            self.output.info(f"Fixed stale paths in {fpath}")
                    except Exception as e:
                        self.output.warning(f"Could not patch {fpath}: {e}")

    def build(self):
        qtbase = self.dependencies["qt5-qtbase"]
        qtdeclarative = self.dependencies["qt5-qtdeclarative"]
        self._fix_qtbase_paths(qtbase.package_folder)
        self._merge_qtdecl_mkspecs(qtdeclarative.package_folder, qtbase.package_folder)

        qmake = os.path.join(qtbase.package_folder, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanException(
                "qt5-qtbase does not provide the required bin/qmake tool"
            )

        build_env = Environment()
        build_env.define("QTDIR", qtbase.package_folder)
        build_env.prepend_path("PATH", os.path.join(qtbase.package_folder, "bin"))
        build_env.append(
            "LD_LIBRARY_PATH",
            os.path.join(qtbase.package_folder, "lib"),
        )
        qtdecl_libdir = os.path.join(qtdeclarative.package_folder, "lib")
        if os.path.isdir(qtdecl_libdir):
            build_env.append("LD_LIBRARY_PATH", qtdecl_libdir)
        qtdecl_qml = os.path.join(qtdeclarative.package_folder, "qml")
        if os.path.isdir(qtdecl_qml):
            build_env.define("QML_IMPORT_PATH", qtdecl_qml)
            build_env.define("QML2_IMPORT_PATH", qtdecl_qml)

        with build_env.vars(self).apply():
            self.run(
                f'cd "{self.source_folder}" && '
                f'{shlex.quote(qmake)} -spec linux-clang qt3d.pro'
            )
            self._fix_makefile_paths(qtbase.package_folder)
            jobs = self.conf.get("tools.build:jobs", default=4, check_type=int)
            self.run(
                f'cd "{self.source_folder}" && make -j{jobs} QMAKE_STRIP=""'
            )

    def package(self):
        src = self.source_folder
        copy(self, "*.so*", src=os.path.join(src, "lib"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.prl", src=os.path.join(src, "lib"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        if os.path.isdir(os.path.join(src, "include")):
            copy(self, "*", src=os.path.join(src, "include"),
                 dst=os.path.join(self.package_folder, "include"), keep_path=True)
        for sub in ("plugins", "qml", "mkspecs", "src"):
            d = os.path.join(src, sub)
            if os.path.isdir(d):
                copy(self, "*", src=d,
                     dst=os.path.join(self.package_folder, sub), keep_path=True)
        bin_dir = os.path.join(src, "bin")
        if os.path.isdir(bin_dir):
            copy(self, "*", src=bin_dir,
                 dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]

        qt5_requires = [
            "qt5-qtbase::Qt5Core",
            "qt5-qtbase::Qt5Gui",
            "qt5-qtbase::Qt5Network",
        ]
        # qt5-qtdeclarative declares no conan components (package-level libs
        # only), so it is referenced via the pkg::pkg self-reference
        # convention; component refs like "qt5-qtdeclarative::Qt5Qml" break
        # the CMakeDeps generator.
        qml_requires = qt5_requires + [
            "qt5-qtdeclarative::qt5-qtdeclarative",
        ]

        # Qt53DCore
        c = self.cpp_info.components["Qt53DCore"]
        c.libs = ["Qt53DCore"]
        c.includedirs = ["include", "include/Qt3DCore"]
        c.requires = qt5_requires
        c.set_property("cmake_file_name", "Qt53DCore")
        c.set_property("cmake_target_name", "Qt5::3DCore")

        # Qt53DRender
        c = self.cpp_info.components["Qt53DRender"]
        c.libs = ["Qt53DRender"]
        c.includedirs = ["include", "include/Qt3DRender"]
        c.requires = ["Qt53DCore"] + qt5_requires
        c.set_property("cmake_file_name", "Qt53DRender")
        c.set_property("cmake_target_name", "Qt5::3DRender")

        # Qt53DInput
        c = self.cpp_info.components["Qt53DInput"]
        c.libs = ["Qt53DInput"]
        c.includedirs = ["include", "include/Qt3DInput"]
        c.requires = ["Qt53DCore"] + qt5_requires
        c.set_property("cmake_file_name", "Qt53DInput")
        c.set_property("cmake_target_name", "Qt5::3DInput")

        # Qt53DLogic
        c = self.cpp_info.components["Qt53DLogic"]
        c.libs = ["Qt53DLogic"]
        c.includedirs = ["include", "include/Qt3DLogic"]
        c.requires = ["Qt53DCore"] + qt5_requires
        c.set_property("cmake_file_name", "Qt53DLogic")
        c.set_property("cmake_target_name", "Qt5::3DLogic")

        # Qt53DAnimation
        c = self.cpp_info.components["Qt53DAnimation"]
        c.libs = ["Qt53DAnimation"]
        c.includedirs = ["include", "include/Qt3DAnimation"]
        c.requires = ["Qt53DCore"] + qt5_requires
        c.set_property("cmake_file_name", "Qt53DAnimation")
        c.set_property("cmake_target_name", "Qt5::3DAnimation")

        # Qt53DExtras
        c = self.cpp_info.components["Qt53DExtras"]
        c.libs = ["Qt53DExtras"]
        c.includedirs = ["include", "include/Qt3DExtras"]
        c.requires = ["Qt53DCore", "Qt53DRender"] + qt5_requires
        c.set_property("cmake_file_name", "Qt53DExtras")
        c.set_property("cmake_target_name", "Qt5::3DExtras")

        # Qt53DQuick
        c = self.cpp_info.components["Qt53DQuick"]
        c.libs = ["Qt53DQuick"]
        c.includedirs = ["include", "include/Qt3DQuick"]
        c.requires = ["Qt53DCore"] + qml_requires
        c.set_property("cmake_file_name", "Qt53DQuick")
        c.set_property("cmake_target_name", "Qt5::3DQuick")

        # Qt53DQuickRender
        c = self.cpp_info.components["Qt53DQuickRender"]
        c.libs = ["Qt53DQuickRender"]
        c.includedirs = ["include", "include/Qt3DQuickRender"]
        c.requires = ["Qt53DCore", "Qt53DRender", "Qt53DQuick"] + qml_requires
        c.set_property("cmake_file_name", "Qt53DQuickRender")
        c.set_property("cmake_target_name", "Qt5::3DQuickRender")

        # Qt53DQuickInput
        c = self.cpp_info.components["Qt53DQuickInput"]
        c.libs = ["Qt53DQuickInput"]
        c.includedirs = ["include", "include/Qt3DQuickInput"]
        c.requires = ["Qt53DCore", "Qt53DInput", "Qt53DQuick"] + qml_requires
        c.set_property("cmake_file_name", "Qt53DQuickInput")
        c.set_property("cmake_target_name", "Qt5::3DQuickInput")

        # Qt53DQuickAnimation
        c = self.cpp_info.components["Qt53DQuickAnimation"]
        c.libs = ["Qt53DQuickAnimation"]
        c.includedirs = ["include", "include/Qt3DQuickAnimation"]
        c.requires = ["Qt53DCore", "Qt53DAnimation", "Qt53DQuick"] + qml_requires
        c.set_property("cmake_file_name", "Qt53DQuickAnimation")
        c.set_property("cmake_target_name", "Qt5::3DQuickAnimation")

        # Qt53DQuickExtras
        c = self.cpp_info.components["Qt53DQuickExtras"]
        c.libs = ["Qt53DQuickExtras"]
        c.includedirs = ["include", "include/Qt3DQuickExtras"]
        c.requires = ["Qt53DCore", "Qt53DExtras", "Qt53DQuick"] + qml_requires
        c.set_property("cmake_file_name", "Qt53DQuickExtras")
        c.set_property("cmake_target_name", "Qt5::3DQuickExtras")

        # Qt53DQuickScene2D
        c = self.cpp_info.components["Qt53DQuickScene2D"]
        c.libs = ["Qt53DQuickScene2D"]
        c.includedirs = ["include", "include/Qt3DQuickScene2D"]
        c.requires = ["Qt53DCore", "Qt53DRender", "Qt53DQuick"] + qml_requires
        c.set_property("cmake_file_name", "Qt53DQuickScene2D")
        c.set_property("cmake_target_name", "Qt5::3DQuickScene2D")

        # Aggregate package-level cmake_file_name
        self.cpp_info.set_property("cmake_file_name", "Qt53D")
