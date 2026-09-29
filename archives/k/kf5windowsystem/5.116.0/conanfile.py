#!/usr/bin/env python3
"""Conan recipe for kf5windowsystem 5.116.0 (KDE Frameworks 5) on HarmonyOS PC.

kwindowsystem is the KDE windowing-system abstraction (builds
libKF5WindowSystem.so). The KF5 branch still targets Qt5, so this package is
the Qt5 counterpart of the published KF6 `kwindowsystem` recipes
(6.14.0 / 6.18.0 / 6.26.0).

Platform backends are QPlugins. Unlike KF6 there is no KWINDOWSYSTEM_X11 /
KWINDOWSYSTEM_WAYLAND option in KF5: the top-level CMakeLists.txt probes the
X11 stack itself and derives KWINDOWSYSTEM_HAVE_X11 from X11_FOUND. OHOS has
no X11/Wayland stack, so X11 is switched off with
CMAKE_DISABLE_FIND_PACKAGE_X11=TRUE, which makes both find_package(X11) calls
(top level and autotests/) skip the search and leave X11_FOUND false. The
library then builds the always-compiled dummy backend
(src/kwindoweffects_dummy.cpp + KWindowSystemPrivateDummy), exactly like the
KF6 recipes with both backends off.

OHOS-specific adaptations (validated on the sibling ki18n5/5.116.0 recipe):
  - QT_MAJOR_VERSION=5 so the project resolves Qt5 (qt5-qtbase/5.15.2.2);
    the project calls find_package(Qt${QT_MAJOR_VERSION}Gui ...).
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS is
    not in the KDE platform list).
  - CMAKE_DISABLE_FIND_PACKAGE_X11=TRUE: no X11 stack on OHOS; the X11 sources
    under src/platforms/xcb are not compiled and the dummy backend provides
    every symbol.
  - BUILD_TESTING=ON: with X11 off upstream registers exactly one CTest test
    (kwindowsystem-platform-wayland-test), which QSKIPs when weston is not on
    PATH. The remaining upstream test targets are marked with
    ecm_mark_as_test(), which only sets EXCLUDE_FROM_ALL and registers no
    CTest test at all, so they never run unattended (blurbehindtest /
    backgroundcontrasttest are interactive GUI demos with no assertions).
  - `ecm_install_po_files_as_qm(poqm)` is dropped by patch: it calls
    find_package(Qt5LinguistTools CONFIG REQUIRED), and Qt5LinguistTools is
    not published to ohpcd. Same adaptation as the KF6 kwindowsystem recipes.
  - ecm is a tool_requires; ecm/6.26.0 satisfies find_package(ECM 5.116.0)
    (minimum-version semantics, same pattern as ki18n5/5.116.0).
  - qt5-qtbase ships per-module cmake configs but no aggregated Qt5Config;
    CMakeDeps regenerates one via cmake_file_name "Qt5" (ki18n5 pattern).
  - CMAKE_AUTOMOC_EXECUTABLE / CMAKE_AUTORCC_EXECUTABLE point at the
    qt5-qtbase bin/moc and bin/rcc (CMakeDeps does not export Qt5::moc/rcc).
  - HarmonyOS is not mapped to the Linux CMake platform, so
    CMAKE_SHARED_LIBRARY_SONAME_<lang>_FLAG is undefined and produced .so
    files would lack DT_SONAME (CI L5 gate). Set the soname flag +
    CMAKE_PLATFORM_NO_VERSIONED_SONAME (expat / ki18n5 validated pattern).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class Kf5WindowSystemConan(ConanFile):
    name = "kf5windowsystem"
    version = "5.116.0"
    description = "KDE Frameworks 5 - KDE Window System (Qt5)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kwindowsystem"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # Regenerate a clean aggregated Qt5Config (qt5-qtbase only ships
        # per-module configs; find_package(Qt5 COMPONENTS ...) needs one).
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["QT_MAJOR_VERSION"] = "5"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # No X11 stack on OHOS. Disabling the package search makes both
        # find_package(X11) calls (top level + autotests/) return not-found,
        # so KWINDOWSYSTEM_HAVE_X11 is false and the dummy backend is used.
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_X11"] = "TRUE"
        # SONAME emission on OHOS (see module docstring).
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        # ECM's CMakeDeps-generated ECMConfig.cmake does not propagate the
        # ECM module locations; set them manually so the KDE cmake modules
        # (KDEInstallDirs, KDECMakeSettings, ECMPoQmTools, ...) are found.
        # ECM_MODULE_DIR is additionally needed by ecm_create_qm_loader(),
        # which configures <ECM_MODULE_DIR>/ECMQmLoader.cpp.in.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_DIR"] = os.path.join(ecm_share, "cmake")
            tc.variables["ECM_MODULE_DIR"] = os.path.join(ecm_share, "modules")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qt5 = self.dependencies["qt5-qtbase"]
        moc_path = os.path.join(qt5.package_folder, "bin", "moc")
        rcc_path = os.path.join(qt5.package_folder, "bin", "rcc")
        if not os.path.isfile(moc_path):
            raise RuntimeError(
                "qt5-qtbase/5.15.2.2 does not provide the required bin/moc tool"
            )
        if not os.path.isfile(rcc_path):
            raise RuntimeError(
                "qt5-qtbase/5.15.2.2 does not provide the required bin/rcc tool"
            )
        tc.variables["CMAKE_AUTOMOC_EXECUTABLE"] = moc_path
        tc.variables["CMAKE_AUTORCC_EXECUTABLE"] = rcc_path

        tc.generate()

        # find_package(ECM 5.116.0 NO_MODULE) needs ECMConfig.cmake on the
        # config-mode search path; find_package(Qt5Gui) needs qtbase's native
        # cmake dir.  The toolchain only populates CMAKE_PREFIX_PATH /
        # CMAKE_MODULE_PATH from its else branch when
        # conan_cmakedeps_paths.cmake does NOT exist - classic CMakeDeps
        # never creates that file, so create it here with the entries the
        # else branch would have provided (plus qtbase's and ECM's).
        extra_paths = []
        if ecm:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            extra_paths.append(
                ('list(PREPEND CMAKE_MODULE_PATH "%s")\n'
                 'list(PREPEND CMAKE_PREFIX_PATH "%s")') % (ecm_cmake, ecm_cmake)
            )
        # The generators folder holds the CMakeDeps-generated Qt5 configs.
        extra_paths.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")\n'
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        qt_pkg = qt5.package_folder
        extra_paths.append(
            ('list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")\n'
             'list(PREPEND CMAKE_LIBRARY_PATH "%s/lib")\n'
             'list(PREPEND CMAKE_INCLUDE_PATH "%s/include")') % (qt_pkg, qt_pkg, qt_pkg)
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w", encoding="utf-8") as f:
            f.write(
                "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)\n"
                + "\n".join(extra_paths) + "\n"
            )

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        # Qt5CoreConfigExtrasMkspecDir.cmake hardcodes
        # <pkg>/../b/mkspecs/linux-clang (a build-tree path that does not
        # exist in the conan cache). ki18n5/5.116.0 validated workaround:
        # copy the mkspecs tree from the package folder to the expected spot.
        source = os.path.join(qt_package_folder, "mkspecs", "linux-clang")
        expected = os.path.join(
            os.path.dirname(qt_package_folder), "b", "mkspecs", "linux-clang"
        )
        if os.path.isdir(source) and not os.path.exists(expected):
            os.makedirs(os.path.dirname(expected), exist_ok=True)
            shutil.copytree(source, expected)

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms are not affected.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        qt5 = self.dependencies["qt5-qtbase"]
        self._prepare_qt_mkspec_compat(qt5.package_folder)
        cmake = CMake(self)
        with self._library_runtime_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _library_runtime_env(self):
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "PATH", os.path.join(dep.package_folder, "bin")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                runtime_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
        for dep in self.dependencies.build.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "CMAKE_PREFIX_PATH", dep.package_folder
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

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
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def _prepare_ctest_runtime_links(self):
        # CTest discovers executables in <build>/bin; their libKF5WindowSystem
        # and Qt5 runtime deps live in the build tree / conan package folders.
        # Symlink them next to the test binaries so the linker resolves.
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
        # The project installs its own KF5WindowSystemConfig.cmake with proper
        # dependency tracking (find_dependency on Qt5Core). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5WindowSystem"]
