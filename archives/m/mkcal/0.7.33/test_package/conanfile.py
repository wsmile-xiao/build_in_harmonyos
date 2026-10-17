#!/usr/bin/env python3
"""Conan test_package for mkcal 0.7.33.

Consumer-side (L1) verification: locate the installed package through the
pkg-config metadata it ships, link a real consumer and round-trip an event
through the SQLite storage backend.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class MkcalTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("pkg-config/0.29.2")

    def layout(self):
        # Keep the test build tree outside the versioned recipe directory so
        # `conan create` cannot leave an unpackaged build tree inside
        # archives/<letter>/<name>/<version>/ (the repository already ignores
        # the .ohc/ runtime directory at its root).
        cmake_layout(
            self,
            build_folder=os.path.join(
                os.pardir, os.pardir, os.pardir, os.pardir, os.pardir,
                ".ohc", "mkcal-test-build",
            ),
        )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        tc.generate()
        self._write_cmake_paths()
        # CMakeToolchain drops a CMakeUserPresets.json next to the conanfile;
        # remove it so the versioned recipe directory stays free of generated
        # files (the build tree itself already lives outside archives/).
        presets = os.path.join(self.recipe_folder, "CMakeUserPresets.json")
        if os.path.exists(presets):
            os.remove(presets)

    def _write_cmake_paths(self):
        """qtbase/kcalendarcore use cmake_find_mode=none, so CMakeDeps does not
        add their lib/cmake directories to CMAKE_PREFIX_PATH."""
        prefixes = []
        libraries = []
        includes = []

        def add_unique(collection, value):
            normalized = value.replace("\\", "/")
            if normalized not in collection:
                collection.append(normalized)

        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                add_unique(prefixes, os.path.join(dep.package_folder, "lib", "cmake"))
                add_unique(prefixes, dep.package_folder)
                add_unique(libraries, os.path.join(dep.package_folder, "lib"))
                add_unique(includes, os.path.join(dep.package_folder, "include"))

        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        with open(os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"), "w") as handle:
            handle.write("\n".join(lines) + "\n")

    def _env(self):
        env = Environment()
        pkgconf = self.dependencies.build.get("pkg-config")
        if pkgconf and pkgconf.package_folder:
            env.prepend_path("PATH", os.path.join(pkgconf.package_folder, "bin"))
        pkg_config_paths = []
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                pkg_config_paths.append(os.path.join(dep.package_folder, "lib", "pkgconfig"))
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
        env.define("PKG_CONFIG_PATH", os.pathsep.join(pkg_config_paths))
        env.define("QT_QPA_PLATFORM", "offscreen")
        if str(self.settings.os) == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return env

    def build(self):
        cmake = CMake(self)
        with self._env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def test(self):
        self._copy_runtime_libs()
        test_exe = os.path.join(self.cpp.build.bindirs[0], "test_mkcal")
        with self._env().vars(self).apply():
            self.run(test_exe, cwd=self.cpp.build.bindirs[0])

    def _copy_runtime_libs(self):
        # OHOS libraries record relative sonames; the musl loader resolves
        # DT_NEEDED entries containing a slash from the process CWD, so keep a
        # copy of every dependency library next to the test binary.
        runtime_dirs = {
            self.cpp.build.bindirs[0],
            self.build_folder,
            os.path.normpath(os.path.join(self.build_folder, os.pardir, os.pardir, "bin")),
        }
        lib_sources = []
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                lib_sources.extend(glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*")))
        for src in lib_sources:
            for runtime_dir in runtime_dirs:
                os.makedirs(runtime_dir, exist_ok=True)
                dst = os.path.join(runtime_dir, os.path.basename(src))
                if os.path.exists(dst) or os.path.abspath(src) == os.path.abspath(dst):
                    continue
                shutil.copy2(src, dst)
