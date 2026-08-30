#!/usr/bin/env python3
"""Conan recipe for ktextwidgets 6.14.0 on HarmonyOS PC.

ktextwidgets is a KDE Frameworks 6 text widgets library (libKF6TextWidgets.so):
KLineEdit/KTextEdit with spell checking (sonnet), completion and configurable
rich-text toolbars.

OHOS-specific adaptations (pattern aligned with published kxmlgui/sonnet
6.x recipes):
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection
  - KF_SKIP_PO_PROCESSING=ON: lconvert (qttools) fails to load libQt6Core
    at build time on this platform; .qm catalogs are not required.
  - WITH_TEXT_TO_SPEECH=OFF: Qt6 TextToSpeech module not published to ohpcd
  - BUILD_TESTING=ON: upstream tests are built and run via ctest (offscreen)
  - Runtime LD_LIBRARY_PATH/QT_PLUGIN_PATH wiring for build-time codegen
    tools and ctest (same helper approach as kxmlgui).
  - ECM_MODULE_PATH set manually (CMakeDeps-generated ECMConfig.cmake does
    not propagate it).
  - Dependencies: kcompletion/6.14.0, kconfig/6.14.0, ki18n/6.14.0,
    kwidgetsaddons/6.14.0, sonnet/6.26.0 (KF6Sonnet CMake package accepts
    >=6.14 <7), qtbase/6.11.1, qtbase-gui/6.11.1, ecm/6.20.0 (tool)
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KtextwidgetsConan(ConanFile):
    name = "ktextwidgets"
    version = "6.14.0"
    description = "KDE Frameworks 6 - Text Widgets"
    license = "LGPL-2.1-or-later"
    homepage = "https://invent.kde.org/frameworks/ktextwidgets"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qtbase-gui/6.11.1")
        self.requires("kcompletion/6.14.0")
        self.requires("kconfig/6.14.0")
        self.requires("ki18n/6.14.0")
        self.requires("kwidgetsaddons/6.14.0")
        # upstream: find_package(KF6Sonnet 6.14.0 REQUIRED) == [6.14.0, 7.0)
        self.requires("sonnet/6.26.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.20.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # Qt6 TextToSpeech is not published to ohpcd.
        tc.variables["WITH_TEXT_TO_SPEECH"] = "OFF"
        # Qt Designer plugin needs Qt6UiPlugin (not published); same guard as
        # the published sonnet recipe.
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated one does not. Set it manually so KDE cmake
        # modules (KDEInstallDirs, KDECMakeSettings, ...) are found.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        CMakeDeps(self).generate()

        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            # Every dependency's lib/cmake dir so find_package(KF6*) and
            # transitive find_dependency() chains resolve.
            for dep in self.dependencies.values():
                if dep and dep.package_folder:
                    lines.append(
                        f'list(PREPEND CMAKE_PREFIX_PATH '
                        f'"{dep.package_folder}/lib/cmake")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_LIBRARY_PATH '
                        f'"{dep.package_folder}/lib")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_INCLUDE_PATH '
                        f'"{dep.package_folder}/include")'
                    )
            lines.append(
                f'list(PREPEND CMAKE_MODULE_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    def _library_runtime_env(self):
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "lib", "plugins"),
                )
                runtime_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
        runtime_env.prepend_path(
            "QT_PLUGIN_PATH", os.path.join(self.build_folder, "bin")
        )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def build(self):
        # Platform guard: OHOS patches only apply on OHOS.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # Build-time tools (moc/uic/kconfig_compiler and this project's
        # Qt6-linked binaries) need the Qt6 runtime resolvable.
        with self._library_runtime_env().vars(self).apply():
            cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
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
        self._patch_ctest_qt_plugin_path()
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def _qt_plugin_path(self):
        plugin_dirs = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                for rel in ("plugins", os.path.join("lib", "plugins")):
                    plugin_dir = os.path.join(dep.package_folder, rel)
                    if os.path.isdir(plugin_dir):
                        plugin_dirs.append(plugin_dir)
        plugin_dirs.append(os.path.join(self.build_folder, "bin"))
        return os.pathsep.join(plugin_dirs)

    def _patch_ctest_qt_plugin_path(self):
        build_bin = os.path.join(self.build_folder, "bin")
        full_plugin_path = self._qt_plugin_path()
        needle = f"QT_PLUGIN_PATH={build_bin}"
        replacement = f"QT_PLUGIN_PATH={full_plugin_path}"
        for test_file in glob.glob(
            os.path.join(self.build_folder, "**", "CTestTestfile.cmake"),
            recursive=True,
        ):
            with open(test_file) as f:
                content = f.read()
            if needle in content:
                with open(test_file, "w") as f:
                    f.write(content.replace(needle, replacement))

    def _prepare_ctest_runtime_links(self):
        # Published KF6 binary packages (sonnet, kconfig, ...) contain
        # DT_NEEDED entries with build-tree-relative paths like
        # "../../bin/libKF6SonnetCore.so". When a ctest binary runs with a
        # CWD of <build>/<subdir>, that path resolves to
        # <build_folder>/../bin — provide a symlink farm of every
        # dependency .so (and our own) there so the loader finds them.
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

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6TextWidgets"]
        self.cpp_info.includedirs = [
            os.path.join("include", "KF6", "KTextWidgets")
        ]
