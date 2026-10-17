import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class GravatarTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        prefixes = [
            dependency.package_folder
            for dependency in self.dependencies.values()
            if dependency and dependency.package_folder
        ]
        toolchain.variables["CMAKE_PREFIX_PATH"] = ";".join(prefixes)
        qtbase = self.dependencies.get("qtbase")
        if qtbase and qtbase.package_folder:
            toolchain.variables["Qt6_DIR"] = os.path.join(
                qtbase.package_folder, "lib", "cmake", "Qt6"
            )
        gravatar = self.dependencies.get("gravatar")
        if gravatar and gravatar.package_folder:
            toolchain.variables["KPim6Gravatar_DIR"] = os.path.join(
                gravatar.package_folder, "lib", "cmake", "KPim6Gravatar"
            )
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # kconfig's package RPATH uses ../../bin. Mirror Conan runtime libraries
        # there so the real consumer executable can load the package graph.
        runtime_bin = os.path.abspath(os.path.join(self.build_folder, "..", "..", "bin"))
        os.makedirs(runtime_bin, exist_ok=True)
        for dependency in self.dependencies.values():
            if not dependency or not dependency.package_folder:
                continue
            lib_dir = os.path.join(dependency.package_folder, "lib")
            if not os.path.isdir(lib_dir):
                continue
            for filename in os.listdir(lib_dir):
                if ".so" not in filename:
                    continue
                source = os.path.join(lib_dir, filename)
                target = os.path.join(runtime_bin, filename)
                if os.path.isfile(source) and not os.path.exists(target):
                    shutil.copy2(source, target)

        run_env = Environment()
        for dependency in self.dependencies.values():
            if dependency and dependency.package_folder:
                run_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dependency.package_folder, "lib")
                )
        kconfig = self.dependencies.get("kconfig")
        if kconfig and kconfig.package_folder:
            run_env.define(
                "LD_PRELOAD",
                os.path.join(kconfig.package_folder, "lib", "libKF6ConfigCore.so"),
            )
        with run_env.vars(self).apply():
            self.run(os.path.join(self.cpp.build.bindir, "test_gravatar"))
