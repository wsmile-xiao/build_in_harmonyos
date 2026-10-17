#!/usr/bin/env python3
"""Conan recipe for qgit 2.13 — Qt GUI git history viewer (OHOS).

qgit is a Qt5 Widgets application (CMake build, upstream supports Qt5/Qt6).
Built natively on aarch64 HarmonyOS PC against qt5-qtbase/5.15.2.2
(Core/Gui/Widgets) using the CMakeDeps-generated Qt5 config package.

Upstream CMakeLists.txt adaptations (patch 0001):
  - Enable CMAKE_AUTOUIC / CMAKE_AUTORCC (AUTOMOC was already on); the
    qt5_wrap_ui() / qt5_add_resources() macros reference the Qt5::uic /
    Qt5::rcc executable targets which the Conan-generated Qt5 config does
    not export, so the .ui files are passed directly to AUTOUIC and
    icons.qrc to AUTORCC (moc/uic/rcc executables are wired via
    CMAKE_AUTOMOC_EXECUTABLE / CMAKE_AUTOUIC_EXECUTABLE /
    CMAKE_AUTORCC_EXECUTABLE in generate()).
  - find_package(QT NAMES ...) is replaced by an explicit
    find_package(Qt5 5.11.0 COMPONENTS Core Gui Widgets) because the
    aggregate Qt5 config does not define the QT_VERSION_MAJOR variable
    the NAMES-trick relies on.

Upstream test suites: qgit ships no test/ directory and registers no
ctest targets (verified: 30 source files, no add_test in CMakeLists.txt).
test_package therefore provides the smoke test: runs the built `qgit`
binary with --version / --help under QT_QPA_PLATFORM=offscreen (both
options exit before the GUI event loop starts).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class QgitConan(ConanFile):
    name = "qgit"
    version = "2.13"
    description = "qgit — a git GUI viewer built on Qt"
    license = "GPL-2.0-only"
    homepage = "https://github.com/tibirna/qgit"
    url = "https://github.com/tibirna/qgit"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    # no_options: an application; no library linkage exported

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _qt_dependency(self):
        return self.dependencies["qt5-qtbase"]

    def generate(self):
        deps = CMakeDeps(self)
        # qt5-qtbase ships per-module cmake configs; CMakeDeps regenerates a
        # clean aggregated Qt5Config so find_package(Qt5 COMPONENTS ...) works
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        qt5 = self._qt_dependency()
        tc = CMakeToolchain(self)
        # Wire the Qt code-generation tools explicitly: the CMakeDeps
        # Qt5 config does not export Qt5::moc/uic/rcc executable targets
        # and AUTOMOC would otherwise fail to locate moc.
        for tool, var in (("moc", "CMAKE_AUTOMOC_EXECUTABLE"),
                          ("uic", "CMAKE_AUTOUIC_EXECUTABLE"),
                          ("rcc", "CMAKE_AUTORCC_EXECUTABLE")):
            tool_path = os.path.join(qt5.package_folder, "bin", tool)
            if not os.path.isfile(tool_path):
                raise RuntimeError(
                    "qt5-qtbase/5.15.2.2 does not provide the required bin/%s tool" % tool
                )
            tc.variables[var] = tool_path
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        with self._runtime_env().vars(self).apply():
            cmake.build()

    def _runtime_env(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
        return env

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
