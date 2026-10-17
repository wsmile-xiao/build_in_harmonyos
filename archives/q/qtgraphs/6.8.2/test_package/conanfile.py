#!/usr/bin/env python3
"""Conan test_package for qtgraphs 6.8.2."""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QtGraphsConanTestConan(ConanFile):
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
        qtshadertools_pkg = self.dependencies["qtshadertools"].package_folder
        pkg = self.dependencies[self.tested_reference_str].package_folder
        tc.cache_variables.update(
            {
                "CMAKE_PREFIX_PATH": qtbase_pkg,
                "CMAKE_MODULE_PATH": os.path.join(
                    qtbase_pkg, "lib", "cmake", "Qt6", "platforms"
                ),
                "Qt6_DIR": os.path.join(qtbase_pkg, "lib", "cmake", "Qt6"),
                "Qt6Qml_DIR": os.path.join(qtdeclarative_pkg, "lib", "cmake", "Qt6Qml"),
                "Qt6Quick_DIR": os.path.join(qtdeclarative_pkg, "lib", "cmake", "Qt6Quick"),
                "Qt6ShaderTools_DIR": os.path.join(qtshadertools_pkg, "lib", "cmake", "Qt6ShaderTools"),
                "Qt6Graphs_DIR": os.path.join(pkg, "lib", "cmake", "Qt6Graphs"),
                "CMAKE_FIND_ROOT_PATH_MODE_PACKAGE": "BOTH",
                "QT_ADDITIONAL_PACKAGES_PREFIX_PATH": ";".join([qtdeclarative_pkg, qtshadertools_pkg, pkg]),
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
            raise ConanException("test_qtgraphs executable directory was not produced")
        cmd = os.path.join(bindirs[0], "test_qtgraphs")
        if not os.path.isfile(cmd):
            raise ConanException("test_qtgraphs executable was not produced: {}".format(cmd))
        if can_run(self):
            self.run(
                "{} timeout 120 {}".format(self._run_env(), shlex.quote(cmd)),
                env="conanrun",
            )
        else:
            self.output.info("test_qtgraphs built for cross profile: {}".format(cmd))

    def _run_env(self):
        lib_paths = []
        qml_paths = []
        plugin_paths = []
        for dep in self.dependencies.values():
            package = dep.package_folder
            for libdir in dep.cpp_info.libdirs or ["lib"]:
                lib_paths.append(os.path.join(package, libdir))
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
