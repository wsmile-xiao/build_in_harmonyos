#!/usr/bin/env python3
"""Conan recipe for qt5-qtx11extras 5.15.2 on OpenHarmony PC."""
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Qt5QtX11ExtrasConan(ConanFile):
    name = "qt5-qtx11extras"
    version = "5.15.2"
    description = "Qt5 X11Extras module providing QX11Info for OpenHarmony"
    license = "LGPL-3.0"
    homepage = "https://www.qt.io/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2")
        # qx11info_x11.cpp 仅依赖 <xcb/xcb.h>，无需 libx11 头文件；
        # libxcb/1.16 不拉 xtrans（与 libx11/6.4.0 的 xtrans/1.6.0 无冲突）
        self.requires("libxcb/1.16")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"qt5-qtx11extras only supports Linux and OHOS, got {self.settings.os}"
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
                self.output.warning(f"Failed to download Qt5 X11Extras source from {url}: {error}")
        raise ConanInvalidConfiguration("Unable to download Qt5 X11Extras source from all mirrors")

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

    def build(self):
        apply_conandata_patches(self)
        src_dir = self.source_folder

        qtbase = self.dependencies["qt5-qtbase"]
        qtbase_pkg = qtbase.package_folder
        libxcb = self.dependencies["libxcb"]

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
        build_env.append("LD_LIBRARY_PATH", os.path.join(qtbase_pkg, "lib"))
        build_env.define("QTDIR", qtbase_pkg)

        # xcb headers for the x11extras subdir (qtbase built without xcb
        # feature, so pass include paths explicitly via CPATH)
        xcb_inc = os.path.join(libxcb.package_folder, "include")
        build_env.append("CPATH", xcb_inc)

        with build_env.vars(self).apply():
            # Configure with qmake. x11extras.pro was patched to link xcb
            # manually (qtbase lacks the xcb qmake module, QMAKE_USE would fail
            # with "Library 'xcb' is not defined"), so pass XCB_INC/XCB_LIB.
            xcb_lib = os.path.join(libxcb.package_folder, "lib")
            self.run(
                f'cd "{src_dir}" && '
                f'"{os.path.join(qtbase_pkg, "bin", "qmake")}" '
                f'qtx11extras.pro -spec linux-clang '
                f'-after "XCB_INC={xcb_inc}" "XCB_LIB={xcb_lib}"'
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
        real_so = None
        if os.path.isdir(pkg_lib):
            for name in sorted(os.listdir(pkg_lib)):
                if name.startswith("libQt5X11Extras.so") and not name.endswith((".prl", ".la", ".pc")):
                    real_so = name
                    break
        if real_so:
            so_path = os.path.join(pkg_lib, real_so)
            for link_name in ("libQt5X11Extras.so", "libQt5X11Extras.so.5", "libQt5X11Extras.so.5.15"):
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
        self.cpp_info.bindirs = ["bin"]

        qtx11extras = self.cpp_info.components["Qt5X11Extras"]
        qtx11extras.libs = ["Qt5X11Extras"]
        # 公开头 qx11info_x11.h 直接 include <xcb/xcb.h>，下游编译必须能看到
        # xcb 头文件；libxcb/1.16 的组件未声明 includedirs（该包自身缺陷），
        # 这里从依赖包显式补充 include 路径。
        libxcb = self.dependencies["libxcb"]
        qtx11extras.includedirs = [
            "include",
            "include/QtX11Extras",
            os.path.join(libxcb.package_folder, "include"),
        ]
        qtx11extras.requires = [
            "qt5-qtbase::Qt5Core",
            "qt5-qtbase::Qt5Gui",
            # qx11info_x11.cpp 直接 include <xcb/xcb.h> 并链接 libxcb
            "libxcb::xcb",
        ]
        qtx11extras.set_property("cmake_file_name", "Qt5X11Extras")
        qtx11extras.set_property("cmake_target_name", "Qt5::X11Extras")
