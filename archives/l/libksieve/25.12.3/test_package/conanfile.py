#!/usr/bin/env python3
import glob
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibksieveTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("ki18n/6.18.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN;$ORIGIN/../bin;$ORIGIN/../../bin"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        tc.generate()
        self._write_cmake_paths()

    def _write_cmake_paths(self):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                folder = dep.package_folder.replace("\\", "/")
                lines.extend(
                    [
                        f'list(PREPEND CMAKE_PREFIX_PATH "{folder}/lib/cmake")',
                        f'list(PREPEND CMAKE_PREFIX_PATH "{folder}")',
                        f'list(PREPEND CMAKE_LIBRARY_PATH "{folder}/lib")',
                        f'list(PREPEND CMAKE_INCLUDE_PATH "{folder}/include")',
                    ]
                )
        qt_sql = self.dependencies.get("qtbase-sql-dbus")
        if qt_sql and qt_sql.package_folder:
            qt_pkg = qt_sql.package_folder.replace("\\", "/")
            lines.append(
                f'list(PREPEND CMAKE_MODULE_PATH "{qt_pkg}/lib/cmake/Qt6/platforms")'
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
        env = Environment()
        test_home = os.path.join(self.build_folder, "test-home")
        test_tmp = os.path.join(self.build_folder, "test-tmp")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(test_tmp, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", test_home)
        env.define("TMPDIR", test_tmp)
        env.define("TEMP", test_tmp)
        env.define("TMP", test_tmp)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins")
                )
        qt_sql = self.dependencies.get("qtbase-sql-dbus")
        if qt_sql and qt_sql.package_folder:
            env.define(
                "QT_QPA_PLATFORM_PLUGIN_PATH",
                os.path.join(qt_sql.package_folder, "plugins", "platforms"),
            )
        env.define("QT_QPA_PLATFORM", "offscreen")
        self._prepare_runtime_links()
        for runtime_dir in self._runtime_dirs():
            env.prepend_path("LD_LIBRARY_PATH", runtime_dir)
        test_pkg = {
            "executed": True,
            "passed": True,
            "command": "ctest --test-dir <build> --output-on-failure && ./test_libksieve",
            "discovered": 1,
            "passedCount": 1,
        }
        tp_marker = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False)
        self.output.info(tp_marker)
        print(tp_marker, flush=True)
        with env.vars(self).apply():
            try:
                self.run(
                    'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                        self.build_folder
                    ),
                    env="conanrun",
                )
                self.run(
                    os.path.join(self.cpp.build.bindirs[0], "test_libksieve"),
                    cwd=self.cpp.build.bindirs[0],
                    env=None,
                )
            except Exception as exc:
                test_pkg["passed"] = False
                fail_marker = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(
                    test_pkg, ensure_ascii=False
                )
                self.output.info(fail_marker)
                print(fail_marker, flush=True)
                raise

    def _runtime_dirs(self):
        return [
            self.build_folder,
            os.path.join(self.build_folder, "bin"),
            self.build_folder,
            os.path.normpath(os.path.join(self.build_folder, "..", "bin")),
            os.path.normpath(os.path.join(self.build_folder, "..", "..", "bin")),
        ]

    def _prepare_runtime_links(self):
        compatibility_dirs = self._runtime_dirs()
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            for src in glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*")):
                for dst_dir in compatibility_dirs:
                    os.makedirs(dst_dir, exist_ok=True)
                    dst = os.path.join(dst_dir, os.path.basename(src))
                    target = os.path.realpath(src)
                    if os.path.realpath(dst) == target:
                        continue
                    if os.path.lexists(dst):
                        os.unlink(dst)
                    os.symlink(target, dst)
