#!/usr/bin/env python3
"""Conan test_package for ki18n 6.18.0.

Verifies that the KF6I18n library can be found via CMake and that the
KI18n API (KLocalizedString) is callable (R34: real API usage).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class Ki18nTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        # test.cpp links Qt6::Qml (provided by the published qtdeclarative
        # split package — ki18n exports it transitively, declare explicitly)
        self.requires("qtdeclarative/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Qt6 split-package component resolution (see main recipe): the
        # top-level Qt6Config from qtbase finds Qml/Quick only through
        # QT_ADDITIONAL_PACKAGES_PREFIX_PATH.
        qt_extra = [
            dep.package_folder for dep in self.dependencies.values()
            if dep and dep.package_folder
            and os.path.isdir(os.path.join(dep.package_folder, "lib", "cmake"))
            and any(n.startswith("Qt6") for n in os.listdir(
                os.path.join(dep.package_folder, "lib", "cmake")))
        ]
        if qt_extra:
            tc.cache_variables[
                "QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)
        tc.generate()

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
        libdirs = [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values() if p.package_folder
        ]
        # libKF6I18nQml.so embeds a relative DT_NEEDED
        # '../../bin/libKF6I18n.so' (in-project link without SONAME path);
        # musl resolves slash-containing NEEDEDs against the process CWD, so
        # mirror the expected layout (kxmlgui/knewstuff pattern) and run
        # with cwd = the exe dir.
        for up in ("..", os.path.join("..", "..")):
            tp_bin = os.path.abspath(os.path.join(self.build_folder, up, "bin"))
            os.makedirs(tp_bin, exist_ok=True)
            for lib in libdirs:
                if os.path.isdir(lib):
                    for name in os.listdir(lib):
                        if name.startswith("libKF6") and ".so" in name:
                            link = os.path.join(tp_bin, name)
                            if not os.path.lexists(link):
                                try:
                                    os.symlink(os.path.join(lib, name), link)
                                except OSError:
                                    pass
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", os.pathsep.join(libdirs))
        with env.vars(self).apply():
            bindir = os.path.abspath(self.cpp.build.bindirs[0])
            exe = os.path.join(bindir, "test_ki18n")
            self.run(f'"{exe}"', cwd=bindir)
