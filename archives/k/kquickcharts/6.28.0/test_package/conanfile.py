#!/usr/bin/env python3
"""Conan test_package for kquickcharts 6.28.0.

The test really exercises the packaged QML module: a C++ consumer links
libQuickCharts.so, spins up a QGuiApplication + QQmlEngine, loads a QML
document that imports org.kde.quickcharts and instantiates BarChart /
LineChart / PieChart, feeds an ArraySource data source into a BarChart, and
reads back a chart-specific property. It runs under offscreen + software
rendering, exactly like the upstream QML autotests.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KQuickChartsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        qtbase_pkg = self.dependencies["qtbase"].package_folder
        qtdeclarative_pkg = self.dependencies["qtdeclarative"].package_folder
        pkg = self.dependencies[self.tested_reference_str].package_folder
        tc.cache_variables.update(
            {
                "CMAKE_PREFIX_PATH": qtbase_pkg,
                "Qt6_DIR": os.path.join(qtbase_pkg, "lib", "cmake", "Qt6"),
                "Qt6Qml_DIR": os.path.join(qtdeclarative_pkg, "lib", "cmake", "Qt6Qml"),
                "Qt6Quick_DIR": os.path.join(qtdeclarative_pkg, "lib", "cmake", "Qt6Quick"),
                "KQUICKCHARTS_LIB_DIR": os.path.join(pkg, "lib"),
            }
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanException("test_kquickcharts executable directory was not produced")
        cmd = os.path.join(bindirs[0], "test_kquickcharts")
        if can_run(self):
            self.run("{} {}".format(self._run_env(), shlex.quote(cmd)), env="conanrun")
        else:
            self.output.info("test_kquickcharts built for cross profile: {}".format(cmd))

    def _run_env(self):
        lib_paths = []
        qml_paths = []
        plugin_paths = []
        for dep in self.dependencies.values():
            package = dep.package_folder
            lib_paths.append(os.path.join(package, "lib"))
            qml_paths.append(os.path.join(package, "qml"))
            plugin_paths.append(os.path.join(package, "plugins"))
        parts = ["QT_QPA_PLATFORM=offscreen", "QT_QUICK_BACKEND=software"]
        if lib_paths:
            parts.append("LD_LIBRARY_PATH={}".format(shlex.quote(os.pathsep.join(lib_paths))))
        if plugin_paths:
            parts.append("QT_PLUGIN_PATH={}".format(shlex.quote(os.pathsep.join(plugin_paths))))
        if qml_paths:
            qml_import = shlex.quote(os.pathsep.join(qml_paths))
            parts.append("QML2_IMPORT_PATH={}".format(qml_import))
            parts.append("QML_IMPORT_PATH={}".format(qml_import))
        return " ".join(parts)
