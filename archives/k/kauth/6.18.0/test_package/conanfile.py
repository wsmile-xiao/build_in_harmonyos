#!/usr/bin/env python3
import os
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KauthTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("kcoreaddons/6.18.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        library_paths = [
            os.path.join(dep.package_folder, "lib")
            for dep in self.dependencies.values()
            if dep and dep.package_folder
        ]
        tc = CMakeToolchain(self)
        tc.variables["CONAN_RUNTIME_LIB_DIRS"] = ";".join(library_paths)
        tc.variables["CMAKE_BUILD_RPATH"] = ";".join(library_paths)
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = (
            "-Wl,--disable-new-dtags,-rpath," + os.pathsep.join(library_paths)
        )
        tc.generate()
        self._write_cmake_paths()

    def _write_cmake_paths(self):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.extend(
                    [
                        f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")',
                        f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")',
                        f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")',
                    ]
                )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        with open(os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"), "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        library_paths = [
            os.path.join(dep.package_folder, "lib")
            for dep in self.dependencies.values()
            if dep and dep.package_folder
        ]
        runtime_prefix = "LD_PRELOAD={} LD_LIBRARY_PATH={}".format(
            shlex.quote(os.path.join(self.dependencies["kauth"].package_folder, "lib", "libKF6AuthCore.so.6")),
            shlex.quote(os.pathsep.join(library_paths)),
        )
        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_kauth")
        # On OHOS the loader does not honour the consumer RPATH here. Pass the
        # Conan dependency directories in the command environment explicitly.
        self.run(
            "if command -v llvm-readelf >/dev/null 2>&1; then "
            "llvm-readelf -d {0}; "
            "elif command -v readelf >/dev/null 2>&1; then "
            "readelf -d {0}; "
            "else echo 'ELF dynamic-section tool unavailable'; fi".format(
                shlex.quote(test_binary)
            ),
            env="",
        )
        self.run(
            "{} {}".format(runtime_prefix, shlex.quote(test_binary)),
            env="",
        )
