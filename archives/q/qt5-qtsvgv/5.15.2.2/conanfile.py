#!/usr/bin/env python3
"""Conan recipe for qt5-qtsvgv 5.15.2.2 on OpenHarmony PC.

qt5-qtsvgv is the repair task's package identity. It keeps the validated
Qt 5.15.2 qmake build while using the published qt5-qtbase/5.15.2 provider.
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Qt5QtSvgvConan(ConanFile):
    name = "qt5-qtsvgv"
    version = "5.15.2.2"
    description = "Qt5 SVG module providing SVG rendering support for OpenHarmony"
    license = "LGPL-3.0"
    homepage = "https://www.qt.io/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The published 5.15.2.2 provider includes the Widgets and Xml
        # modules required by the complete Qt SVG upstream test suite.
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"qt5-qtsvgv only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        source_data = self.conan_data["sources"]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get(
                    self,
                    url=url,
                    sha256=source_data["sha256"],
                    strip_root=True,
                )
                return
            except ConanException as error:
                self.output.warning(f"Failed to download Qt5 SVG source from {url}: {error}")
        raise ConanInvalidConfiguration("Unable to download Qt5 SVG source from all mirrors")

    def _fix_qtbase_paths(self, qtbase_pkg):
        """Fix qt5-qtbase package's qt.conf and .pri files to use the package
        directory instead of the original build directory."""
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

        # Rebind text metadata that can retain the provider's Conan build or
        # package directory. qmake consumes .pri/.prl files transitively, and
        # libtool/pkg-config/CMake metadata can expose the same stale roots.
        build_dir_patterns = [
            re.compile(r"(/[^\s]*/\.conan2/p/b/qt5-[A-Za-z0-9]+/b)(?=/|$)"),
            re.compile(r"(/[^\s]*/\.conan2/p/b/qt5-[A-Za-z0-9]+/p)(?=/|$)"),
            re.compile(
                r"([A-Za-z]:[\\/][^\s]+[\\/]conan-home[\\/]p[\\/]"
                r"qt5-[A-Za-z0-9]+[\\/]p)(?=[\\/]|$)"
            ),
        ]
        metadata_suffixes = (".pri", ".prl", ".la", ".pc", ".cmake")
        for metadata_root, _dirs, metadata_files in os.walk(qtbase_pkg):
            for metadata_name in metadata_files:
                if not metadata_name.endswith(metadata_suffixes):
                    continue
                metadata_path = os.path.join(metadata_root, metadata_name)
                with open(metadata_path, "r", encoding="utf-8") as f:
                    content = f.read()
                fixed_content = content
                for build_dir_pattern in build_dir_patterns:
                    fixed_content = build_dir_pattern.sub(
                        lambda _match: qtbase_pkg, fixed_content
                    )
                if fixed_content != content:
                    with open(metadata_path, "w", encoding="utf-8") as f:
                        f.write(fixed_content)

    def build(self):
        apply_conandata_patches(self)
        src_dir = self.source_folder

        qtbase = self.dependencies["qt5-qtbase"]
        qtbase_pkg = qtbase.package_folder

        # Fix qt5-qtbase paths (qt.conf and .pri files point to build dir)
        self._fix_qtbase_paths(qtbase_pkg)

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c")
        cxx = compilers.get("cpp") or compilers.get("cxx")

        build_env = Environment()
        if cc:
            build_env.define("CC", cc)
        if cxx:
            build_env.define("CXX", cxx)
        build_env.prepend_path("PATH", os.path.join(qtbase_pkg, "bin"))
        # Preserve the worker SDK runtime libraries (including libxml2 for
        # lld) while adding the provider's Qt libraries.
        build_env.append_path("LD_LIBRARY_PATH", os.path.join(qtbase_pkg, "lib"))
        build_env.define("QTDIR", qtbase_pkg)

        with build_env.vars(self).apply():
            # Configure with qmake
            self.run(
                f'cd "{src_dir}" && '
                f'"{os.path.join(qtbase_pkg, "bin", "qmake")}" '
                f'qtsvg.pro -spec linux-clang'
            )

            # Build (prevent stripping - OHOS loader rejects stripped ELF)
            jobs = self.conf.get("tools.build:jobs", default=2, check_type=int)
            self.run(f'cd "{src_dir}" && make -j{jobs} QMAKE_STRIP=""')

    def package(self):
        src_dir = self.source_folder

        # Copy libraries (unstripped)
        lib_dir = os.path.join(src_dir, "lib")
        copy(self, "*.so*", src=lib_dir,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.prl", src=lib_dir,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.la", src=lib_dir,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.pc", src=lib_dir,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

        # Ensure library symlinks exist (HMDFS may not preserve them during copy)
        import shutil
        pkg_lib = os.path.join(self.package_folder, "lib")
        # 动态查找实际库文件（不硬编码 .so.5.15.2，兼容不同构建产物命名）
        real_so = None
        if os.path.isdir(pkg_lib):
            for name in sorted(os.listdir(pkg_lib)):
                if name.startswith("libQt5Svg.so") and not name.endswith((".prl", ".la", ".pc")):
                    real_so = name
                    break
        if real_so:
            so_path = os.path.join(pkg_lib, real_so)
            for link_name in ("libQt5Svg.so", "libQt5Svg.so.5", "libQt5Svg.so.5.15"):
                link_path = os.path.join(pkg_lib, link_name)
                if link_path == so_path:
                    continue
                if not os.path.exists(link_path) and os.path.exists(so_path):
                    try:
                        os.symlink(real_so, link_path)
                    except OSError:
                        shutil.copy2(so_path, link_path)

        # Copy headers
        include_dir = os.path.join(src_dir, "include")
        if os.path.isdir(include_dir):
            copy(self, "*", src=include_dir,
                 dst=os.path.join(self.package_folder, "include"), keep_path=True)

        # Copy source headers (Qt forwarding headers reference src/)
        copy(self, "*.h", src=os.path.join(src_dir, "src"),
             dst=os.path.join(self.package_folder, "src"), keep_path=True)

        # Copy plugins
        plugins_dir = os.path.join(src_dir, "plugins")
        if os.path.isdir(plugins_dir):
            copy(self, "*", src=plugins_dir,
                 dst=os.path.join(self.package_folder, "plugins"), keep_path=True)

        # Copy mkspecs modules
        mkspecs_dir = os.path.join(src_dir, "mkspecs")
        if os.path.isdir(mkspecs_dir):
            copy(self, "*", src=mkspecs_dir,
                 dst=os.path.join(self.package_folder, "mkspecs"), keep_path=True)

        # Copy cmake configs
        cmake_dir = os.path.join(lib_dir, "cmake")
        if os.path.isdir(cmake_dir):
            copy(self, "*", src=cmake_dir,
                 dst=os.path.join(self.package_folder, "lib", "cmake"), keep_path=True)

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]

        qt5svg = self.cpp_info.components["Qt5Svg"]
        qt5svg.libs = ["Qt5Svg"]
        qt5svg.includedirs = ["include", "include/QtSvg"]
        qt5svg.requires = ["qt5-qtbase::Qt5Core", "qt5-qtbase::Qt5Gui"]
        qt5svg.set_property("cmake_file_name", "Qt5Svg")
        qt5svg.set_property("cmake_target_name", "Qt5::Svg")
