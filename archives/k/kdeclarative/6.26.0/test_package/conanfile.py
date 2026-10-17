#!/usr/bin/env python3
"""Conan test_package for kdeclarative 6.26.0."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KdeclarativeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("qtdeclarative/6.11.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
        qtdeclarative = self.dependencies.get("qtdeclarative")
        if qtdeclarative and qtdeclarative.package_folder:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{qtdeclarative.package_folder}/lib/cmake")'
            )
            lines.append(
                f'list(PREPEND CMAKE_LIBRARY_PATH '
                f'"{qtdeclarative.package_folder}/lib")'
            )
        for dep_name in ("qtdeclarative", "qtshadertools"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH '
                    f'"{dep.package_folder}/lib")'
                )
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH '
                    f'"{dep.package_folder}/include")'
                )
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def _test_build_env(self):
        """Environment for configure/build/test.

        ECM 6.26 modules pulled in through KF6DeclarativeConfig run the
        qtbase qtpaths host tool during configure (ecm_query_qt). Prepend
        /system/lib64 + the SDK llvm lib so the compatible libc++_shared.so
        wins over the sandbox bundle copy (kconfig 6.26.0 precedent).
        """
        build_env = Environment()
        if self.settings.os == "OHOS":
            import glob as _glob
            for llvm_lib in sorted(
                _glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "bin")
                )
        return build_env

    def build(self):
        cmake = CMake(self)
        with self._test_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def test(self):
        env = self._test_build_env()
        env.define("QT_QPA_PLATFORM", "offscreen")
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kdeclarative"),
                env="conanrun",
            )
