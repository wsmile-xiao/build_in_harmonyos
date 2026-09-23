#!/usr/bin/env python3
"""Conan recipe for kdbusaddons 6.18.0 on HarmonyOS PC."""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KdbusaddonsConan(ConanFile):
    name = "kdbusaddons"
    version = "6.18.0"
    description = "KDE Frameworks 6 - DBus convenience classes"
    license = "LGPL-2.1-only OR LGPL-3.0-only"
    homepage = "https://invent.kde.org/frameworks/kdbusaddons"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase-sql-dbus/6.11.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["WITH_X11"] = "OFF"
        self._define_ecm(tc)
        self._write_cmake_paths()
        tc.generate()

    def _define_ecm(self, tc):
        ecm = self.dependencies.build.get("ecm")
        if not ecm:
            return
        ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
        tc.variables["ECM_MODULE_PATH"] = ";".join(
            os.path.join(ecm_share, rel)
            for rel in ("modules", "find-modules", "kde-modules")
        )

    def _write_cmake_paths(self):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if not dep or not dep.package_folder:
                continue
            lines.extend(
                [
                    f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")',
                    f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")',
                    f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")',
                ]
            )
        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            lines.extend(
                [
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_share}/cmake")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/find-modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/kde-modules")',
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
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        test_env = Environment()
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
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            test_env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
            test_env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            test_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        if not shutil.which("dbus-daemon") and not shutil.which("dbus-launch"):
            self.output.info(
                "Skipping kdbusservicetest: it requires a DBus session bus, "
                "but this OHOS package profile provides neither dbus-daemon "
                "nor dbus-launch"
            )
            with test_env.vars(self).apply():
                self.run('ctest --test-dir "{}" -N'.format(self.build_folder))
            return
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6DBusAddons"]
