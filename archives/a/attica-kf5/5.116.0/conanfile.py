#!/usr/bin/env python3
"""Conan recipe for Attica KF5 5.116.0 on HarmonyOS PC.

Attica is the KDE Frameworks 5 Open Collaboration Services client library.

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - BUILD_TESTING=ON and ctest execution for upstream autotests
  - Dependencies: qt5-qtbase/5.15.2 and ecm/6.20.0 (ECM)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its lib/cmake
    builddir to CMAKE_PREFIX_PATH
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    load,
    save,
)


class AtticaConan(ConanFile):
    name = "attica-kf5"
    version = "5.116.0"
    description = "KDE Frameworks 5 - Open Collaboration Services client library"
    license = "LGPL-2.1-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL"
    homepage = "https://invent.kde.org/frameworks/attica"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2")

    def build_requirements(self):
        self.tool_requires("ecm/6.20.0")

    def layout(self):
        cmake_layout(self, generator="Ninja")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        shared = bool(self.options.shared)
        tc.variables["BUILD_SHARED_LIBS"] = shared
        tc.variables["ATTICA_STATIC_BUILD"] = not shared
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # The published Qt package may contain a build-tree mkspec path.
        # Attica has its own prefix, so KDE does not need Qt install paths.
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"

        # A cross build on Windows cannot execute the target AArch64 moc.
        # Keep the target Qt package as the dependency, but allow the caller
        # to provide a native Qt5 moc through a Conan conf.
        for cmake_var, tool_path in self._host_qt_tools().items():
            tc.variables[cmake_var] = self._cmake_path(tool_path)

        if str(self.settings.os) in ("Linux", "OHOS"):
            if str(self.settings.os) == "OHOS":
                tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = (
                    "-Wl,-soname,libKF5Attica.so"
                )
                compilers = self.conf.get(
                    "tools.build:compiler_executables", default={}, check_type=dict
                ) or {}
                compiler = compilers.get("c") or compilers.get("cpp")
                if compiler:
                    native_dir = os.path.dirname(
                        os.path.dirname(os.path.dirname(os.path.abspath(compiler)))
                    )
                    sysroot = os.path.join(native_dir, "sysroot")
                    if os.path.isdir(sysroot):
                        tc.variables["CMAKE_SYSROOT"] = self._cmake_path(sysroot)

                targets = {
                    "armv8": "aarch64-linux-ohos",
                    "x86_64": "x86_64-linux-ohos",
                }
                target = targets.get(str(self.settings.arch))
                if target:
                    tc.variables["CMAKE_C_COMPILER_TARGET"] = target
                    tc.variables["CMAKE_CXX_COMPILER_TARGET"] = target

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = self._cmake_path(
                os.path.join(ecm.package_folder, "share", "ECM")
            )
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    f"{ecm_share}/modules",
                    f"{ecm_share}/find-modules",
                    f"{ecm_share}/kde-modules",
                ]
            )

        qtbase = self.dependencies.get("qt5-qtbase")
        if qtbase:
            self._prepare_qt_mkspec_compat(qtbase.package_folder)
            qt_pkg = self._cmake_path(qtbase.package_folder)
            lines = [
                f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")',
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")',
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")',
            ]
            if ecm:
                ecm_pkg = self._cmake_path(ecm.package_folder)
                ecm_cmake = f"{ecm_pkg}/share/ECM/cmake"
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')

            lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    @staticmethod
    def _cmake_path(path):
        return os.fspath(path).replace("\\", "/")

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        source = os.path.join(qt_package_folder, "mkspecs", "linux-clang")
        expected = os.path.join(
            os.path.dirname(qt_package_folder), "b", "mkspecs", "linux-clang"
        )
        if os.path.isdir(source) and not os.path.exists(expected):
            os.makedirs(os.path.dirname(expected), exist_ok=True)
            shutil.copytree(source, expected)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        with self._library_runtime_env().vars(self).apply():
            cmake.build()
        self._run_upstream_tests()

    def _library_runtime_env(self):
        runtime_env = Environment()
        host_tools = self._host_qt_tools()
        if host_tools:
            runtime_env.prepend_path(
                "PATH", os.path.dirname(next(iter(host_tools.values())))
            )
        host_runtime = self.conf.get(
            "user.attica-kf5:qt_host_runtime_dir", default="", check_type=str
        )
        if host_runtime:
            runtime_env.prepend_path("PATH", os.path.abspath(os.fspath(host_runtime)))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                runtime_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        return runtime_env

    def _host_moc_path(self):
        path = self.conf.get("user.attica-kf5:qt_host_moc", default="", check_type=str)
        if not path:
            return ""
        path = os.path.abspath(os.fspath(path))
        if not os.path.isfile(path):
            raise ConanInvalidConfiguration(
                "user.attica-kf5:qt_host_moc does not point to a file: " + path
            )
        return path

    def _host_qt_tools(self):
        tools_dir = self.conf.get(
            "user.attica-kf5:qt_host_tools_dir", default="", check_type=str
        )
        if not tools_dir:
            moc = self._host_moc_path()
            if moc:
                tools_dir = os.path.dirname(moc)
        if not tools_dir:
            return {}

        tools_dir = os.path.abspath(os.fspath(tools_dir))
        if not os.path.isdir(tools_dir):
            raise ConanInvalidConfiguration(
                "user.attica-kf5:qt_host_tools_dir is not a directory: " + tools_dir
            )
        tools = {}
        for name, cmake_var in (
            ("moc", "CMAKE_AUTOMOC_EXECUTABLE"),
            ("rcc", "CMAKE_AUTORCC_EXECUTABLE"),
            ("uic", "CMAKE_AUTOUIC_EXECUTABLE"),
        ):
            path = os.path.join(tools_dir, name + ".exe")
            if not os.path.isfile(path):
                raise ConanInvalidConfiguration(
                    "missing Qt host tool for Attica: " + path
                )
            tools[cmake_var] = path
        return tools

    def _run_upstream_tests(self):
        if not can_run(self):
            self.output.info(
                "Skipping upstream CTest during cross-compilation; target execution is required on OHOS"
            )
            return
        test_env = self._library_runtime_env()
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
        self._prepare_ctest_runtime_links()
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error -E "^providertest$"'.format(
                    self.build_folder
                )
            )

    def _prepare_ctest_runtime_links(self):
        compatibility_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, "bin")
        )
        os.makedirs(compatibility_bin, exist_ok=True)
        lib_sources = glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*"))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        for src in lib_sources:
            dst = os.path.join(compatibility_bin, os.path.basename(src))
            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    os.symlink(src, dst)
                except OSError:
                    shutil.copy2(src, dst)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._make_pkgconfig_relocatable()

    def _make_pkgconfig_relocatable(self):
        package_root = self._cmake_path(self.package_folder).rstrip("/")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        for pc_file in glob.glob(os.path.join(pc_dir, "*.pc")):
            content = load(self, pc_file)
            content = content.replace(
                f"prefix={package_root}", "prefix=${pcfiledir}/../..", 1
            )
            content = content.replace(
                f"libdir={package_root}/lib", "libdir=${prefix}/lib", 1
            )
            content = content.replace(
                f"includedir={package_root}/include", "includedir=${prefix}/include", 1
            )
            content = content.replace(f"-L{package_root}/lib", "-L${libdir}")
            content = content.replace(f"-I{package_root}/include", "-I${includedir}")
            save(self, pc_file, content)

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5Attica"]
