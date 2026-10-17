#!/usr/bin/env python3
"""Conan recipe for qtspeech-opensource-src 5.15.15 on OpenHarmony PC.

Qt Speech provides text-to-speech capabilities for Qt applications.
On platforms without a speech engine (like OHOS without speech-dispatcher
or flite), the module builds with the mock backend, which provides the
full API surface but without actual TTS audio output.
"""
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class QtSpeechOpenSourceSrcConan(ConanFile):
    name = "qtspeech-opensource-src"
    version = "5.15.15"
    description = "Qt5 Speech module - provides text-to-speech on OpenHarmony"
    license = "LGPL-3.0"
    homepage = "https://www.qt.io/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    def export_sources(self):
        export_conandata_patches(self)

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

    def _fix_qtdecl_paths(self, qtdecl_pkg, qtbase_pkg):
        """Fix qt5-qtdeclarative .pri files to reference the correct
        package directories instead of the original build directory,
        and merge them into qt5-qtbase's mkspecs/modules."""
        qtbase_modules = os.path.join(qtbase_pkg, "mkspecs", "modules")
        qtbase_modules_inst = os.path.join(qtbase_pkg, "mkspecs", "modules-inst")

        build_dir_pattern = re.compile(
            r"/[^\s]*/p/b/qt5-q[0-9a-f]+/b"
        )

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
                fixed_content = build_dir_pattern.sub(qtdecl_pkg, content)
                dst_dir = qtbase_modules if modules_dir_name == "modules" else qtbase_modules_inst
                os.makedirs(dst_dir, exist_ok=True)
                dst_path = os.path.join(dst_dir, pri_file)
                with open(dst_path, "w", encoding="utf-8") as f:
                    f.write(fixed_content)

    def build(self):
        apply_conandata_patches(self)
        src_dir = self.source_folder

        qtbase = self.dependencies["qt5-qtbase"]
        qtbase_pkg = qtbase.package_folder
        qtdecl = self.dependencies["qt5-qtdeclarative"]
        qtdecl_pkg = qtdecl.package_folder

        # Fix qt5-qtbase paths (qt.conf and .pri files point to build dir)
        self._fix_qtbase_paths(qtbase_pkg)
        # Fix qt5-qtdeclarative paths and merge .pri into qtbase mkspecs
        self._fix_qtdecl_paths(qtdecl_pkg, qtbase_pkg)

        qmake = os.path.join(qtbase_pkg, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanException(
                "qt5-qtbase does not provide the required bin/qmake tool"
            )

        build_env = Environment()
        build_env.define("QTDIR", qtbase_pkg)
        build_env.prepend_path("PATH", os.path.join(qtbase_pkg, "bin"))
        build_env.append("LD_LIBRARY_PATH", os.path.join(qtbase_pkg, "lib"))
        build_env.append("LD_LIBRARY_PATH", os.path.join(qtdecl_pkg, "lib"))

        with build_env.vars(self).apply():
            self.run(
                f'cd "{src_dir}" && '
                f'{shlex.quote(qmake)} -spec linux-clang qtspeech.pro'
            )
            jobs = self.conf.get("tools.build:jobs", default=2, check_type=int)
            self.run(f'cd "{src_dir}" && make -j{jobs} QMAKE_STRIP=""')

    def package(self):
        src = self.source_folder

        # Copy libraries (unstripped)
        lib_dir = os.path.join(src, "lib")
        if os.path.isdir(lib_dir):
            copy(self, "*.so*", src=lib_dir,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
            copy(self, "*.prl", src=lib_dir,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
            copy(self, "*.la", src=lib_dir,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
            copy(self, "*.pc", src=lib_dir,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)

        # Copy QML plugins
        qml_dir = os.path.join(src, "qml")
        if os.path.isdir(qml_dir):
            copy(self, "*", src=qml_dir,
                 dst=os.path.join(self.package_folder, "qml"), keep_path=True)

        # Copy headers
        include_dir = os.path.join(src, "include")
        if os.path.isdir(include_dir):
            copy(self, "*", src=include_dir,
                 dst=os.path.join(self.package_folder, "include"), keep_path=True)

        # Copy source headers (Qt forwarding headers reference src/)
        copy(self, "*.h", src=os.path.join(src, "src"),
             dst=os.path.join(self.package_folder, "src"), keep_path=True)

        # Copy mkspecs modules
        mkspecs_dir = os.path.join(src, "mkspecs")
        if os.path.isdir(mkspecs_dir):
            copy(self, "*", src=mkspecs_dir,
                 dst=os.path.join(self.package_folder, "mkspecs"), keep_path=True)

        # Copy cmake configs
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
        self.cpp_info.set_property("cmake_file_name", "Qt5TextToSpeech")

        qt5texttospeech = self.cpp_info.components["Qt5TextToSpeech"]
        qt5texttospeech.libs = ["Qt5TextToSpeech"]
        qt5texttospeech.includedirs = ["include", "include/QtTextToSpeech"]
        qt5texttospeech.requires = [
            "qt5-qtbase::Qt5Core",
            "qt5-qtbase::Qt5Gui",
            "qt5-qtdeclarative::qt5-qtdeclarative",
        ]
        qt5texttospeech.set_property("cmake_target_name", "Qt5::TextToSpeech")
