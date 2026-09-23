#!/usr/bin/env python3
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class GrantleeThemeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        self._write_cmake_paths()

    def _write_cmake_paths(self):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.extend(
                    [
                        f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")',
                        f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}")',
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
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self._prepare_runtime_links()
        env = Environment()
        runtime_dirs = [
            self.cpp.build.bindirs[0],
            os.path.normpath(os.path.join(self.build_folder, "..", "..", "bin")),
        ]
        for runtime_dir in runtime_dirs:
            env.prepend_path("LD_LIBRARY_PATH", runtime_dir)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins")
                )
        test_tmp = os.path.join(self.build_folder, "test-tmp")
        os.makedirs(test_tmp, exist_ok=True)
        env.define("TMPDIR", test_tmp)
        env.define("TEMP", test_tmp)
        env.define("TMP", test_tmp)
        # qtpaths/test 可执行文件运行依赖兼容的 libc++_shared.so（bluez-qt
        # 6.28.0 先例）：本机 LD_LIBRARY_PATH 的 bundle/libs/arm64 段含不
        # 兼容版本，前置 /system/lib64 保证 C++ 符号正确解析。
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        test_exe = os.path.join(self.cpp.build.bindirs[0], "test_grantleetheme")
        with env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )
            self.run(test_exe, cwd=self.cpp.build.bindirs[0])

    def _prepare_runtime_links(self):
        runtime_dirs = [
            self.cpp.build.bindirs[0],
            os.path.normpath(os.path.join(self.build_folder, "..", "..", "bin")),
        ]
        for runtime_dir in runtime_dirs:
            os.makedirs(runtime_dir, exist_ok=True)
        for dep in self.dependencies.values():
            libdir = os.path.join(dep.package_folder, "lib") if dep.package_folder else None
            if not libdir or not os.path.isdir(libdir):
                continue
            for src in glob.glob(os.path.join(libdir, "lib*.so*")):
                for runtime_dir in runtime_dirs:
                    dst = os.path.join(runtime_dir, os.path.basename(src))
                    if os.path.exists(dst):
                        continue
                    shutil.copy2(src, dst)
