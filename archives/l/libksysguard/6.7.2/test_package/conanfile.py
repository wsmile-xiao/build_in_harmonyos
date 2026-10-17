#!/usr/bin/env python3
"""Conan test_package for libksysguard 6.7.2."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibksysguardTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # KSysGuard::Formatter's imported target links Qt6::Qml; the Qml
        # component config lives in the separate qtdeclarative package
        # (kdeclarative 6.26.0 test_package precedent).
        self.requires("qtdeclarative/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        """libksysguard ships its upstream KSysGuardConfig.cmake with
        cmake_find_mode=none, so consumers resolve find_package(KSysGuard)
        from the package folder itself; the same is true for every KF6 and
        Qt6 dependency (all published with their real config files). Feed
        every dependency package folder into CMAKE_PREFIX_PATH through the
        toolchain instead of relying on CMakeDeps-generated configs."""
        tc = CMakeToolchain(self)
        prefixes = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                prefixes.append(dep.package_folder)
                prefixes.append(os.path.join(dep.package_folder, "lib", "cmake"))
        if prefixes:
            tc.variables["CMAKE_PREFIX_PATH"] = ";".join(prefixes)
        tc.generate()

    def _test_build_env(self):
        """Runtime environment for configure/build/test.

        Prepend the SDK llvm lib so the compatible libc++_shared.so wins over
        the sandbox bundle copy (kconfig 6.26.0 precedent), plus every host
        dependency's lib dir for soname resolution.
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
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_libksysguard"),
                env="conanrun",
            )
