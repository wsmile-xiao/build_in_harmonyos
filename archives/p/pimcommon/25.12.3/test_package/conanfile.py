#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv


class PimcommonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("kio/6.14.0")
        self.requires("kcodecs/6.14.0")
        self.requires("kcolorscheme/6.14.0")
        self.requires("kconfig/6.14.0")
        self.requires("kcoreaddons/6.14.0")
        self.requires("ki18n/6.14.0")
        self.requires("kitemviews/6.14.0")
        self.requires("kjobwidgets/6.14.0")
        self.requires("kwidgetsaddons/6.14.0")
        self.requires("kxmlgui/6.14.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()

        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"

        dep = self.dependencies.get("pimcommon")
        if dep and dep.package_folder:
            tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
        tc.generate()
        self._write_cmake_paths()

    def _write_cmake_paths(self):
        prefixes = []
        preferred = (
            "pimcommon",
            "qtbase-sql-dbus",
            "kio",
            "kcodecs",
            "kcolorscheme",
            "kconfig",
            "kcoreaddons",
            "ki18n",
            "kitemviews",
            "kjobwidgets",
            "kwidgetsaddons",
            "kxmlgui",
        )
        for dep_name in preferred:
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                prefixes.extend((
                    os.path.join(dep.package_folder, "lib", "cmake"),
                    dep.package_folder,
                ))
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            ref_name = dep.ref.name
            if ref_name in ("qtbase", "qtbase-sql-dbus"):
                continue
            prefixes.extend((
                os.path.join(dep.package_folder, "lib", "cmake"),
                dep.package_folder,
            ))
        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            prefixes.append(os.path.join(ecm_share, "cmake"))
        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            'list(PREPEND CMAKE_PREFIX_PATH "{}")'.format(";".join(prefixes)),
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        with open(
            os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"), "w"
        ) as paths_file:
            paths_file.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _prepare_relative_needed_links(self):
        # Build-tree relative DT_NEEDED entries ("../../bin/libKF6*.so")
        # in published KF6 binaries resolve relative to the process cwd;
        # provide links at the plausible bin/ locations around the build
        # folder (keditbookmarks 26.04.0 / ktextwidgets / kxmlgui precedent).
        import glob as _glob
        import shutil
        bases = [
            self.build_folder,
            os.path.normpath(os.path.join(self.build_folder, os.pardir)),
            os.path.normpath(os.path.join(self.build_folder, os.pardir,
                                          os.pardir)),
        ]
        sources = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                sources.extend(_glob.glob(
                    os.path.join(dep.package_folder, "lib", "lib*.so*")))
        for base in bases:
            root = os.path.join(base, "bin")
            os.makedirs(root, exist_ok=True)
            for src in sources:
                dst = os.path.join(root, os.path.basename(src))
                if os.path.exists(src) and not os.path.lexists(dst):
                    try:
                        os.symlink(src, dst)
                    except OSError:
                        shutil.copy2(src, dst)

    def test(self):
        # The test binary is an OHOS aarch64 executable and this host is an
        # OHOS PC: run it directly with the dependency lib dirs plus the
        # system libc++ dir on LD_LIBRARY_PATH (akonadi 25.12.3 test_package
        # precedent), after preparing build-tree-relative NEEDED links.
        self._prepare_relative_needed_links()
        env = Environment()
        folders = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder and dep.package_folder not in folders:
                folders.append(dep.package_folder)
        for folder in reversed(folders):
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(folder, "lib"))
            env.prepend_path("QT_PLUGIN_PATH", os.path.join(folder, "plugins"))
            env.prepend_path(
                "QT_PLUGIN_PATH", os.path.join(folder, "lib", "plugins"))
        # Prepend LAST so it ends up FIRST: the SDK aarch64-linux-ohos/libc++.so
        # is a linker script the runtime loader cannot use; the compatible
        # libc++_shared.so is in /system/lib64 (keditbookmarks precedent).
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("HOME", os.path.join(self.build_folder, "test-home"))
        env.define("XDG_RUNTIME_DIR", self.build_folder)
        with env.vars(self, scope="run").apply():
            self.run("ctest --output-on-failure", cwd=self.build_folder, env=None)
