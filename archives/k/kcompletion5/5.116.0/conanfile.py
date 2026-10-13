#!/usr/bin/env python3
"""Conan recipe for KDE Frameworks KCompletion 5.116.0 on HarmonyOS PC."""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class Kcompletion5Conan(ConanFile):
    name = "kcompletion5"
    version = "5.116.0"
    description = "KDE Frameworks 5 completion widgets for Qt 5"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kcompletion"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")
        self.requires("kconfig5/5.116.0")
        self.requires("kwidgetsaddons5/5.116.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self, generator="Ninja")

    def source(self):
        source = self.conan_data["sources"]
        get(self, **source, strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # qt5-qtbase exports per-module configs, so generate the Qt5 umbrella
        # config required by the KDE Frameworks CMake files.
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        tc = CMakeToolchain(self, generator="Ninja")
        tc.variables["QT_MAJOR_VERSION"] = "5"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        # HarmonyOS is not mapped to the Linux SONAME defaults in CMake.
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        qt5 = self.dependencies["qt5-qtbase"]
        self._prepare_qt_mkspec_compat(qt5.package_folder)
        tool_paths = {
            "CMAKE_AUTOMOC_EXECUTABLE": os.path.join(qt5.package_folder, "bin", "moc"),
            "CMAKE_AUTORCC_EXECUTABLE": os.path.join(qt5.package_folder, "bin", "rcc"),
            "CMAKE_AUTOUIC_EXECUTABLE": os.path.join(qt5.package_folder, "bin", "uic"),
        }
        for variable, path in tool_paths.items():
            if not os.path.isfile(path):
                raise RuntimeError("qt5-qtbase/5.15.2.2 is missing required tool: %s" % path)
            tc.variables[variable] = path

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    os.path.join(ecm_share, "modules"),
                    os.path.join(ecm_share, "find-modules"),
                    os.path.join(ecm_share, "kde-modules"),
                ]
            )

        # ECM's Qt query and KF5ConfigConfig.cmake also use the native Qt
        # module configs (not only the aggregate Qt5 config from CMakeDeps).
        # Expose the Qt package prefix and ECM config path explicitly.
        qt_folder = self._cmake_path(qt5.package_folder)
        paths = [
            'list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")' % qt_folder,
            'list(PREPEND CMAKE_LIBRARY_PATH "%s/lib")' % qt_folder,
            'list(PREPEND CMAKE_INCLUDE_PATH "%s/include")' % qt_folder,
        ]
        for dependency_name in ("kconfig5", "kwidgetsaddons5"):
            dependency = self.dependencies.get(dependency_name)
            if dependency:
                dependency_folder = self._cmake_path(dependency.package_folder)
                paths.append(
                    'list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")'
                    % dependency_folder
                )
        if ecm:
            ecm_folder = self._cmake_path(ecm.package_folder)
            ecm_cmake = "%s/share/ECM/cmake" % ecm_folder
            paths.extend(
                [
                    'list(PREPEND CMAKE_MODULE_PATH "%s")' % ecm_cmake,
                    'list(PREPEND CMAKE_PREFIX_PATH "%s")' % ecm_cmake,
                ]
            )
        paths.extend(
            [
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            ]
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w", encoding="utf-8") as paths_cmake:
            paths_cmake.write("\n".join(paths) + "\n")

        tc.generate()
        # CMakeDeps Qt5 imported targets omit these definitions; QtTest uses
        # them to select the GUI-aware QTest APIs used by upstream tests.
        toolchain_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        with open(toolchain_file, "a", encoding="utf-8") as toolchain:
            toolchain.write(
                "\n# Restore Qt5 module definitions normally exported by Qt configs.\n"
                "add_compile_definitions(QT_CORE_LIB QT_GUI_LIB QT_WIDGETS_LIB QT_TEST_LIB)\n"
            )

    @staticmethod
    def _cmake_path(path):
        return os.fspath(path).replace("\\", "/")

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        # The Qt module configs point to ../b/mkspecs/linux-clang; a downloaded
        # binary package contains the source tree only under package_folder.
        source = os.path.join(qt_package_folder, "mkspecs")
        destination = os.path.join(os.path.dirname(qt_package_folder), "b", "mkspecs")
        if not os.path.isdir(source):
            return
        for relative in ("linux-clang", "common"):
            source_tree = os.path.join(source, relative)
            destination_tree = os.path.join(destination, relative)
            if (
                os.path.isdir(source_tree)
                and not os.path.islink(destination_tree)
                and not os.path.isdir(destination_tree)
            ):
                os.makedirs(os.path.dirname(destination_tree), exist_ok=True)
                shutil.copytree(source_tree, destination_tree)

    def build(self):
        if str(self.settings.os) == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._build_environment().vars(self).apply():
            cmake.configure()
            cmake.build()
            self._run_upstream_tests()

    def _runtime_environment(self):
        runtime_env = Environment()
        for dependency in self.dependencies.values():
            if dependency and dependency.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dependency.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dependency.package_folder, "plugins")
                )
                runtime_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dependency.package_folder, "plugins", "platforms"),
                )
        for relative in ("bin", "lib"):
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, relative))
        return runtime_env

    def _build_environment(self):
        build_env = self._runtime_environment()
        if str(self.settings.os) == "OHOS":
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            for llvm_lib in sorted(
                glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        return build_env

    def _run_upstream_tests(self):
        if not can_run(self):
            self.output.info("Skipping upstream CTest: target binaries cannot run on this build host.")
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
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "%s" --output-on-failure --no-tests=error --timeout 60'
                % self.build_folder
            )

    def package(self):
        CMake(self).install()

    def package_info(self):
        # Use the upstream KF5CompletionConfig.cmake and exported KF5::Completion target.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5Completion"]
