#!/usr/bin/env python3
import glob
import os
import shutil
import shlex
import stat

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class SonnetTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        runtime_libs = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_libs.append(os.path.join(dep.package_folder, "lib"))
        # Embed dependency locations so the OHOS loader does not rely on
        # Conan cache symlink aliases at test runtime.
        if runtime_libs:
            toolchain.variables["CMAKE_BUILD_RPATH"] = ";".join(runtime_libs)
            toolchain.variables["CMAKE_INSTALL_RPATH"] = ";".join(runtime_libs)
        toolchain.generate()
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
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        runtime_dir = self._prepare_runtime_links()
        env = Environment()
        library_paths = [runtime_dir]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                libdir = os.path.join(dep.package_folder, "lib")
                library_paths.append(libdir)
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins"))
        env.define("QT_QPA_PLATFORM", "offscreen")
        test_exe = os.path.join(runtime_dir, "test_sonnet")
        # The Conan cache is non-executable to the OHOS app launcher. Libraries
        # were copied to runtime_dir above, beside the executable, so dlopen()
        # must use this allowed absolute directory instead.
        runtime_prefix = "SONNET_RUNTIME_DIR={} LD_LIBRARY_PATH={} QT_QPA_PLATFORM=offscreen".format(
            shlex.quote(runtime_dir), shlex.quote(os.pathsep.join(library_paths))
        )
        with env.vars(self).apply():
            self.run(
                '{} ctest --test-dir {} --output-on-failure --no-tests=error'.format(
                    runtime_prefix, shlex.quote(self.build_folder)
                ),
                env="",
            )
            self.run('{} {}'.format(runtime_prefix, shlex.quote(test_exe)), env="")

    def _prepare_runtime_links(self):
        runtime_dir = os.path.abspath(self.build_folder)
        os.makedirs(runtime_dir, exist_ok=True)
        for dep in self.dependencies.values():
            libdir = os.path.join(dep.package_folder, "lib") if dep.package_folder else None
            if not libdir or not os.path.isdir(libdir):
                continue
            for src in glob.glob(os.path.join(libdir, "lib*.so*")):
                dst = os.path.join(runtime_dir, os.path.basename(src))
                if os.path.abspath(src) == os.path.abspath(dst):
                    continue
                # Copy the target rather than retaining cache-relative symlinks.
                # OHOS requires execute permission when a shared object is
                # mapped by dlopen(), while Conan cache artifacts are 0644.
                shutil.copy2(src, dst, follow_symlinks=True)
                os.chmod(dst, os.stat(dst).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        # HMDFS may not resolve Conan's versioned symlink aliases. Materialize
        # the SONAME names required by the test executable.
        for stem in ("libKF6SonnetCore", "libKF6SonnetUi"):
            target = os.path.join(runtime_dir, stem + ".so.6")
            if not os.path.isfile(target):
                candidates = glob.glob(os.path.join(runtime_dir, stem + ".so.*"))
                candidates = [p for p in candidates if os.path.basename(p) != stem + ".so.6"]
                if candidates:
                    shutil.copy2(candidates[0], target)
                    os.chmod(target, os.stat(target).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            if not os.path.isfile(target):
                raise RuntimeError("Missing consumer runtime library: {}".format(os.path.basename(target)))
        return runtime_dir
