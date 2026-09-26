#!/usr/bin/env python3
"""Conan test_package for libkmahjongg 26.04.0.

Verifies that KMahjongglib6 can be found via CMake and that the
KMahjonggTileset API is callable (R34: real API usage).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibkmahjonggTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("kconfig/6.14.0")
        self.requires("kconfigwidgets/6.14.0")
        self.requires("kcoreaddons/6.14.0")
        self.requires("kwidgetsaddons/6.14.0")
        self.requires("ki18n/6.14.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        # qtsvg is cmake_find_mode=none; set Qt6Svg_DIR so Qt6Config.cmake
        # (from qtbase) can resolve the Svg component.
        qtsvg = self.dependencies.get("qtsvg")
        if qtsvg:
            tc.variables["Qt6Svg_DIR"] = os.path.join(
                qtsvg.package_folder, "lib", "cmake", "Qt6Svg"
            )

        qtbase = self.dependencies.get("qtbase")
        pkg = self.dependencies.get(
            self.tested_reference_str.split("/")[0]
        )
        lines = [
            'set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)',
        ]
        if pkg:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{pkg.package_folder}/lib/cmake")'
            )
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{qt_pkg}/lib/cmake")'
            )
            lines.append(
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")'
            )
            lines.append(
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")'
            )
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH '
                    f'"{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH '
                    f'"{dep.package_folder}/include")'
                )
        lines.append(
            f'list(PREPEND CMAKE_PREFIX_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        lines.append(
            f'list(PREPEND CMAKE_MODULE_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # KF6 libraries record build-tree-relative DT_NEEDED entries like
        # "../../bin/libKF6ConfigCore.so"; mirror the expected layout under
        # <build_folder>/../../bin by symlinking every KF6 shared library
        # (and our own KMahjongg6 library) there (same helper as
        # ktextwidgets test_package).
        tp_bin = os.path.join(self.build_folder, "..", "..", "bin")
        os.makedirs(tp_bin, exist_ok=True)
        for dep in self.dependencies.values():
            libdir = (
                os.path.join(dep.package_folder, "lib")
                if dep.package_folder
                else None
            )
            if libdir and os.path.isdir(libdir):
                for name in os.listdir(libdir):
                    if name.startswith("libKF6") and name.endswith(".so"):
                        link = os.path.join(tp_bin, name)
                        if not os.path.lexists(link):
                            os.symlink(os.path.join(libdir, name), link)
        # Our own libKMahjongg6 shared library must also be visible to the
        # test binary via the same symlink farm.
        for name in ("libKMahjongg6.so", "libKMahjongg6.so.6"):
            libdir = os.path.join(
                self.dependencies[self.tested_reference_str.split("/")[0]].package_folder,
                "lib",
            )
            src = os.path.join(libdir, name)
            link = os.path.join(tp_bin, name)
            if os.path.exists(src) and not os.path.lexists(link):
                os.symlink(src, link)

        env = Environment()
        env.append("LD_LIBRARY_PATH", [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ])
        env.append("LD_LIBRARY_PATH", tp_bin)
        env.define("QT_QPA_PLATFORM", "offscreen")
        # KMahjonggTileset::loadDefault() locates the default tileset via
        # QStandardPaths::GenericDataLocation
        # (share/kmahjongglib/tilesets/default.desktop); point XDG_DATA_DIRS
        # at the packaged share dir so the real data file is found (without
        # this the test fails even though the library is packaged correctly).
        pkg = self.dependencies[self.tested_reference_str.split("/")[0]]
        if pkg and pkg.package_folder:
            share_dir = os.path.join(pkg.package_folder, "share")
            if os.path.isdir(share_dir):
                env.append("XDG_DATA_DIRS", share_dir)
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libkmahjongg")
        # Apply the extra environment (XDG_DATA_DIRS pointing at the packaged
        # share dir, plus LD_LIBRARY_PATH) around the conanrun-wrapped run so
        # KMahjonggTileset::loadDefault() can locate the real tileset data.
        with env.vars(self).apply():
            self.run(test_bin, env="conanrun")
