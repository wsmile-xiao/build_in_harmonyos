#!/usr/bin/env python3
"""Conan consumer test for kdecoration3/6.7.0."""
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class Kdecoration3TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("ki18n/6.26.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_CXX_FLAGS"] = "-std=c++20"
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        tc.variables["KDECORATION3_OHOS"] = self.settings.os == "OHOS"
        tc.generate()

        package = self.dependencies.get("kdecoration3")
        qtbase = self.dependencies.get("qtbase")
        ki18n = self.dependencies.get("ki18n")
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dependency in (package, qtbase, ki18n):
            if dependency and dependency.package_folder:
                lines.append(
                    "list(PREPEND CMAKE_PREFIX_PATH "
                    f'"{dependency.package_folder}/lib/cmake")'
                )
                lines.append(
                    "list(PREPEND CMAKE_LIBRARY_PATH "
                    f'"{dependency.package_folder}/lib")'
                )
                lines.append(
                    "list(PREPEND CMAKE_INCLUDE_PATH "
                    f'"{dependency.package_folder}/include")'
                )
        lines.extend([
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ])
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning(
                "Cross-built consumer executable cannot run on the build host"
            )
            return

        runtime_env = Environment()
        for dependency in self.dependencies.values():
            if dependency.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH",
                    os.path.join(dependency.package_folder, "lib"),
                )
        if self.settings.os == "OHOS":
            # The consumer binary also needs the OHOS C++ runtime. Locate it
            # from the configured compiler so both native workers and local
            # cross-runner layouts work without a fixed SDK version.
            runtime_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            compiler_config = self.conf.get(
                "tools.build:compiler_executables", default={}
            )
            compiler = (
                compiler_config.get("c")
                if isinstance(compiler_config, dict)
                else None
            )
            if compiler:
                compiler_dir = os.path.dirname(os.path.realpath(compiler))
                candidates = [
                    os.path.join(
                        compiler_dir, "..", "lib", "aarch64-linux-ohos"
                    ),
                    os.path.join(
                        compiler_dir,
                        "..",
                        "ohos-sdk.org",
                        "*",
                        "ohos",
                        "native",
                        "llvm",
                        "lib",
                        "aarch64-linux-ohos",
                    ),
                    os.path.join(compiler_dir, "..", "lib"),
                ]
                for pattern in candidates:
                    matches = glob.glob(pattern)
                    if matches and os.path.isdir(matches[0]):
                        runtime_env.prepend_path(
                            "LD_LIBRARY_PATH", os.path.realpath(matches[0])
                        )
                        break
        with runtime_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure '
                "--no-tests=error".format(self.build_folder),
                env="conanrun",
            )
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kdecoration3"),
                env="conanrun",
            )
            if self.settings.os == "OHOS":
                self.run(
                    os.path.join(
                        self.cpp.build.bindirs[0],
                        "test_kdecoration3_ohos",
                    ),
                    env="conanrun",
                )
