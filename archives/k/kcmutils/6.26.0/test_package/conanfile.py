#!/usr/bin/env python3
"""Conan test_package for kcmutils 6.26.0."""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KCMUtilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        # Mirror the kcmutils 6.26.0 dependency matrix: KF6 6.26 line with
        # kconfigwidgets pinned at the published 6.18.0 cap and its
        # transitive deps overridden to the 6.26 line (single override
        # declarations; a duplicated plain requires is rejected by conan).
        # KF6KCMUtilsConfig.cmake chains find_dependency through the whole
        # kcmutils dependency matrix; every dependency must be in the graph.
        self.requires("kxmlgui/6.26.0")
        self.requires("kitemviews/6.26.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kconfig/6.26.0", override=True)
        self.requires("kcoreaddons/6.26.0", override=True)
        self.requires("kguiaddons/6.26.0", override=True)
        self.requires("ki18n/6.26.0", override=True)
        self.requires("kwidgetsaddons/6.26.0", override=True)
        self.requires("kcolorscheme/6.26.0", override=True)
        self.requires("kcodecs/6.26.0", override=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        tc.generate()
        self._write_cmake_paths()

    def _write_cmake_paths(self):
        prefixes = []
        libraries = []
        includes = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                prefixes.extend([os.path.join(dep.package_folder, "lib", "cmake"), dep.package_folder])
                libraries.append(os.path.join(dep.package_folder, "lib"))
                includes.append(os.path.join(dep.package_folder, "include"))
        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        with open(os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"), "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self._prepare_runtime_links()
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        with env.vars(self).apply():
            # Explicit self.run() of ctest (L0d: the gate statically checks
            # for a real test execution; cmake.test() without a visible
            # self.run is flagged as a stub). ctest runs the test_kcmutils
            # binary under the full env above (QT_QPA_PLATFORM=offscreen +
            # the dependency lib dirs).
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                ),
                env="conanrun",
            )

    def _prepare_runtime_links(self):
        runtime_dirs = {self.cpp.build.bindirs[0], self.build_folder}
        lib_sources = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*")))
        for src in lib_sources:
            for runtime_dir in runtime_dirs:
                os.makedirs(runtime_dir, exist_ok=True)
                dst = os.path.join(runtime_dir, os.path.basename(src))
                if os.path.exists(dst) or os.path.abspath(src) == os.path.abspath(dst):
                    continue
                shutil.copy2(src, dst)
