#!/usr/bin/env python3
"""Conan test_package for kitemviews5 5.116.0 (L1 official test).

Consumer-side verification (R34): the C++ test links KF5::ItemViews and drives
the real public API — KListWidgetSearchLine, KTreeWidgetSearchLine,
KFilterProxySearchLine, KCategorizedSortFilterProxyModel, KCategorizedView and
KCategoryDrawer — asserting observable behaviour, not just that the library
links.

HarmonyOS-specific assertions (R53): test.cpp additionally asserts that
  * QApplication runs on the HarmonyOS "offscreen" QPA platform plugin (the
    headless GUI path a Widgets library uses on OHOS);
  * the loaded libKF5ItemViews.so carries the OHOS-required unversioned
    DT_SONAME and a DT_RUNPATH (E537: the installed ELF is linked with its
    final install RPATH and is never rewritten post-link, so OHOS keeps
    mmap'ing it PROT_EXEC).

test() really executes the built binary through self.run() (L0d / R34).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class KItemViews5TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        qt5 = self.dependencies.get("qt5-qtbase")
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if pkg:
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH "{}/lib/cmake")'.format(pkg.package_folder)
            )
        if qt5:
            qt_pkg = qt5.package_folder
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "{}/lib/cmake")'.format(qt_pkg))
            lines.append('list(PREPEND CMAKE_LIBRARY_PATH "{}/lib")'.format(qt_pkg))
            lines.append('list(PREPEND CMAKE_INCLUDE_PATH "{}/include")'.format(qt_pkg))
        # The generators folder holds the CMakeDeps-generated Qt5 configs.
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
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
        if not can_run(self):
            return
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_kitemviews5"),
            env="conanrun",
        )
