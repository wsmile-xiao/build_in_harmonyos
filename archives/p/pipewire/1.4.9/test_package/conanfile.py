#!/usr/bin/env python3
"""Conan test_package — pipewire 1.4.9 L1 test."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PipewireTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        lib_dirs = []
        spa_plugin_dir = None
        module_dir = None
        for name, dep in self.dependencies.items():
            if getattr(dep.cpp_info, "libdirs", None):
                for d in dep.cpp_info.libdirs:
                    lib_dirs.append(os.path.join(dep.package_folder, d))
            if getattr(dep.cpp_info, "libdirs", None):
                for d in dep.cpp_info.libdirs:
                    p = os.path.join(dep.package_folder, d)
                    cand = os.path.join(p, "spa-0.2")
                    if os.path.isdir(cand):
                        spa_plugin_dir = cand
                    cand = os.path.join(p, "pipewire-0.3")
                    if os.path.isdir(cand):
                        module_dir = cand
        env_parts = []
        if lib_dirs:
            env_parts.append("LD_LIBRARY_PATH=" + os.pathsep.join(lib_dirs))
        if spa_plugin_dir:
            env_parts.append("SPA_PLUGIN_DIR=" + spa_plugin_dir)
        if module_dir:
            env_parts.append("PIPEWIRE_MODULE_DIR=" + module_dir)
        env = " ".join(env_parts)
        bindir = self.cpp.build.bindirs[0]
        for exe in ("test_pipewire", "test_ohos"):
            test_bin = os.path.join(bindir, exe)
            self.run(f'{env} "{test_bin}"')