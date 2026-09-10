#!/usr/bin/env python3
"""Conan recipe for KDecoration3 6.7.0 on HarmonyOS PC (CMake)."""
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class Kdecoration3Conan(ConanFile):
    name = "kdecoration3"
    version = "6.7.0"
    description = "KDE Plasma window-decoration plugin interface library"
    license = "LGPL-2.1-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL"
    homepage = "https://invent.kde.org/plasma/kdecoration"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("ki18n/6.26.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["BUILD_TESTING"] = "ON"
        toolchain.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        toolchain.variables["CMAKE_CXX_STANDARD"] = "20"
        toolchain.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        toolchain.variables["CMAKE_CXX_FLAGS"] = "-std=c++20"
        toolchain.variables["KDECORATION3_OHOS"] = (
            self.settings.os == "OHOS"
        )
        # The SDK defaults package lookup to its sysroot only. Conan
        # dependencies and host-side ECM live outside that sysroot.
        toolchain.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        toolchain.variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = "ON"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            toolchain.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qtbase = self.dependencies.get("qtbase")
        ki18n = self.dependencies.get("ki18n")
        if qtbase:
            lines = [
                f'list(PREPEND CMAKE_PREFIX_PATH "{qtbase.package_folder}/lib/cmake")',
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qtbase.package_folder}/lib")',
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qtbase.package_folder}/include")',
            ]
            if ki18n:
                lines.extend([
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ki18n.package_folder}/lib/cmake")',
                    f'list(PREPEND CMAKE_LIBRARY_PATH "{ki18n.package_folder}/lib")',
                    f'list(PREPEND CMAKE_INCLUDE_PATH "{ki18n.package_folder}/include")',
                ])
            if ecm:
                ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
                lines.extend([
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")',
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")',
                ])
            lines.extend([
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            ])
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w", encoding="utf-8") as handle:
                handle.write("\n".join(lines) + "\n")

        toolchain.generate()

        toolchain_file = os.path.join(
            self.generators_folder, "conan_toolchain.cmake"
        )
        with open(toolchain_file, "a", encoding="utf-8") as handle:
            handle.write(
                "\n# CMake has no HarmonyOS SONAME platform rule.\n"
                'set(CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG "-Wl,-soname,")\n'
            )

    def build(self):
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)

        cmake = CMake(self)
        with self._runtime_environment().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _runtime_environment(self):
        runtime_env = Environment()
        for dependency in self.dependencies.values():
            if dependency and dependency.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH",
                    os.path.join(dependency.package_folder, "lib"),
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dependency.package_folder, "plugins"),
                )

        if self.settings.os == "OHOS":
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

        for relative_dir in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH",
                os.path.join(self.build_folder, relative_dir),
            )
        return runtime_env

    def _run_upstream_tests(self):
        if not can_run(self):
            self.output.warning(
                "Cross-built upstream tests cannot run on the build host"
            )
            return

        test_env = self._runtime_environment()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define(
            "XDG_DATA_HOME", os.path.join(test_home, ".local", "share")
        )
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure '
                "--no-tests=error --timeout 90".format(self.build_folder)
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["kdecorations3", "kdecorations3private"]
