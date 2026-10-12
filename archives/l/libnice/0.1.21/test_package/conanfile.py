#!/usr/bin/env python3
"""Conan consumer tests for libnice 0.1.21."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibNiceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = (
        "CMakeToolchain",
        "PkgConfigDeps",
        "VirtualRunEnv",
        "VirtualBuildEnv",
    )

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _runtime_library_dirs(self):
        paths = []
        for dependency in self.dependencies.values():
            package_folder = dependency.package_folder
            if not package_folder:
                continue
            for libdir in dependency.cpp_info.libdirs:
                path = libdir if os.path.isabs(libdir) else os.path.join(package_folder, libdir)
                if os.path.isdir(path) and path not in paths:
                    paths.append(path)
        return paths

    def build(self):
        cmake = CMake(self)
        rpaths = self._runtime_library_dirs()
        variables = {}
        if rpaths:
            linker_flags = ["-Wl,--disable-new-dtags"]
            linker_flags.extend("-Wl,-rpath," + path for path in rpaths)
            variables["CMAKE_EXE_LINKER_FLAGS"] = " ".join(linker_flags)

        cmake.configure(variables=variables)
        cmake.build()

    @staticmethod
    def _bash():
        return (os.environ.get("CONFIG_SHELL") or shutil.which("bash")
                or "/data/service/hnp/bin/bash")

    def _run_with_runtime_libraries(self, command):
        library_path = os.pathsep.join(self._runtime_library_dirs())
        shell_command = "export LD_LIBRARY_PATH={}\"${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; {}".format(
            shlex.quote(library_path), command
        )
        self.run(
            shlex.join([self._bash(), "-c", shell_command]),
            env="conanrun",
        )

    def test(self):
        consumer = os.path.join(self.build_folder, self.cpp.build.bindirs[0], "test_consumer")
        self._run_with_runtime_libraries("exec " + shlex.quote(consumer))
