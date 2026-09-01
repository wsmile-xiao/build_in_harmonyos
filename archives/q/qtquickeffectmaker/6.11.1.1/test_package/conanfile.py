#!/usr/bin/env python3
"""Conan test_package for qtquickeffectmaker 6.11.1."""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QtQuickEffectMakerConanTestConan(ConanFile):
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
                "CMAKE_FIND_ROOT_PATH_MODE_PACKAGE": "BOTH",
                "QT_ADDITIONAL_PACKAGES_PREFIX_PATH": ";".join([qtdeclarative_pkg, qtshadertools_pkg]),
            }
        )
        tc.generate()


    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _test_binary(self):
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanException("test_qtquickeffectmaker executable directory was not produced")
        cmd = os.path.join(bindirs[0], "test_qtquickeffectmaker")
        if not os.path.isfile(cmd):
            raise ConanException("test_qtquickeffectmaker executable was not produced: {}".format(cmd))
        return cmd

    def _qqem_binary(self):
        dependency = self.dependencies[self.tested_reference_str]
        bindirs = dependency.cpp_info.bindirs or ["bin"]
        names = ["qqem"]
        if str(self.settings.os) == "Windows":
            names.insert(0, "qqem.exe")
        for bindir in bindirs:
            for name in names:
                candidate = os.path.join(dependency.package_folder, bindir, name)
                if os.path.isfile(candidate):
                    return candidate
        raise ConanException("qqem tool binary was not packaged under: {}".format(
            ", ".join(os.path.join(dependency.package_folder, bindir) for bindir in bindirs)
        ))

    def test(self):
        test_binary = self._test_binary()
        qqem_binary = self._qqem_binary()
        if can_run(self):
            self.run("{} {} {}".format(
                self._run_env(), shlex.quote(test_binary), shlex.quote(qqem_binary)),
                env="conanrun")
        else:
            for binary in (test_binary, qqem_binary):
                self.run("file {}".format(shlex.quote(binary)))
                self.run("readelf -h {}".format(shlex.quote(binary)))
                self.run("readelf -d {}".format(shlex.quote(binary)))
            self.output.info("qtquickeffectmaker cross binary metadata verified: {}, {}".format(
                test_binary, qqem_binary))

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
