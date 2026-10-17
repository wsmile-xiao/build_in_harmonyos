#!/usr/bin/env python3
"""Conan test_package for kglobalaccel 5.116.0.

Verifies that the KF5GlobalAccel CMake package can be found and that the
public KGlobalAccel API is callable (R34: real API usage, no stub test).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KglobalaccelTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Qt5 Widgets is a PUBLIC link dependency and the installed
        # KF5GlobalAccelConfig.cmake calls find_dependency(Qt5DBus/Qt5Widgets).
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.generate()

        for dep in self.dependencies.values():
            if dep and dep.ref.name == "qt5-qtbase":
                self._prepare_qt_mkspec_compat(dep.package_folder)

        lines = [
            'set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)',
        ]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")'
                )
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")')
                lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        # The installed KF5GlobalAccelConfig.cmake calls find_dependency(Qt5DBus)
        # which pulls in the native Qt5Core config; Qt5CoreConfigExtras probes
        # <qt_pkg>/../b/mkspecs/linux-clang (absent in the published package).
        # Mirror it (attica-kf5/5.116.0 precedent).
        source = os.path.join(qt_package_folder, "mkspecs", "linux-clang")
        expected = os.path.join(
            os.path.dirname(qt_package_folder), "b", "mkspecs", "linux-clang"
        )
        if os.path.isdir(source) and not os.path.exists(expected):
            os.makedirs(os.path.dirname(expected), exist_ok=True)
            shutil.copytree(source, expected)

    def build(self):
        # OHOS SDK lld depends on libxml2.so.16 shipped in the SDK llvm/lib
        # directory; prepend it so CMake TryCompile can link (kcrash/kconfig
        # 6.26.0 precedent).
        env = Environment()
        for llvm_lib in (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib",
        ):
            if os.path.isdir(llvm_lib):
                env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        env = Environment()
        env.append("LD_LIBRARY_PATH", [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ])
        env.define("QT_QPA_PLATFORM", "offscreen")
        if self.settings.os == "OHOS":
            # The sandbox LD_LIBRARY_PATH can shadow the compatible
            # libc++_shared.so; /system/lib64 must win (kconfig/kcrash
            # 6.26.0 precedent).
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
            if os.path.isdir(llvm_lib):
                env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        # Point QStandardPaths at private writable dirs so the consumer test
        # neither touches nor warns about the shared runtime directory
        # (XDG_RUNTIME_DIR not set / not owned warnings).
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", test_home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kglobalaccel"),
                env="conanrun",
            )
