#!/usr/bin/env python3
"""Conan recipe for kwindowsystem5 5.116.0 (KDE Frameworks 5) on HarmonyOS PC.

kwindowsystem is the KDE Frameworks 5 window-system abstraction library
(builds libKF5WindowSystem).  The KF5 branch still targets Qt5.

OHOS-specific adaptations:
  - Depends on the full OHOS Qt5 package (qt/5.15.19) rather than the minimal
    qt5-qtbase/5.15.2: kwindowsystem PUBLIC-links Qt5::Widgets, and the
    published qt5-qtbase/5.15.2 OHOS binary only ships QtCore/QtGui/QtTest
    (no QtWidgets).  qt/5.15.19 ships the complete per-module Qt5Config.cmake
    files (cmake_find_mode=none), so the project's per-module
    find_package(Qt5Gui / Qt5Widgets / Qt5Test) resolve natively.
  - QT_MAJOR_VERSION=5 so the project selects the Qt5 branch.
  - KF_IGNORE_PLATFORM_CHECK=TRUE bypasses CDE platform detection (OHOS is
    not in the KDE platform list).
  - ECM_MODULE_PATH is set explicitly because the project's CMakeLists.txt
    does `set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH})`, and ecm is a
    tool_requires (build context) so its share/ECM tree is not on the host
    config path automatically.
  - poqm translation is disabled (see patches/0001-poqm): it requires
    Qt5LinguistTools / lrelease, which the packaged Qt5 does not ship.  The
    .ts files are not runtime-essential on OHOS.
  - X11/XCB support is not built: OHOS has no X11, so find_package(X11)
    leaves KWINDOWSYSTEM_HAVE_X11=0 and the X11-free (dummy) backend is
    compiled.  libKF5WindowSystem still exposes the full KWindowSystem /
    KWindowInfo / KWindowEffects API.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class Kwindowsystem5Conan(ConanFile):
    name = "kwindowsystem5"
    version = "5.116.0"
    description = "KDE Frameworks 5 - window system integration library"
    license = "LGPL-2.1-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL"
    homepage = "https://invent.kde.org/frameworks/kwindowsystem"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Full OHOS Qt5: provides Qt5Widgets (kwindowsystem PUBLIC-links it),
        # Qt5Gui, Qt5Core and Qt5Test (autotests) with native per-module
        # Qt5Config.cmake files.
        self.requires("qt/5.15.19")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.variables["QT_MAJOR_VERSION"] = "5"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # HarmonyOS is not mapped to the Linux CMake platform, so
        # CMAKE_SHARED_LIBRARY_SONAME_<lang>_FLAG stays undefined and the
        # produced shared library would have no ELF DT_SONAME (the W3 CI L5
        # soname gate fails).  Keep SONAME emission (relocatable) but skip
        # versioned symlinks, which some OHOS/HMDFS build paths reject.
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        # ecm is a tool_requires (build context) so its share/ECM tree is not
        # wired into the host config path automatically.
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

            # find_package(ECM 5.116.0 NO_MODULE) is config-mode: it looks for
            # ECMConfig.cmake and honors the ECM_DIR cache variable directly.
            # The KF5 kwindowsystem CMakeLists also calls feature_summary()
            # FATAL_ON_MISSING_REQUIRED_PACKAGES, so a missing ECM_DIR aborts
            # configure.  Pin ECM_DIR to the ecm package's cmake dir.
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            tc.variables["ECM_DIR"] = ecm_cmake

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        with self._library_runtime_env().vars(self).apply():
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
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                runtime_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
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
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5WindowSystem"]
