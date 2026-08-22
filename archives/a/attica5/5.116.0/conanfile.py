#!/usr/bin/env python3
"""Conan recipe for attica5 5.116.0 (KDE Frameworks 5) on HarmonyOS PC.

Attica is the KDE Frameworks 5 Open Collaboration Services client library
(builds libKF5Attica). The KF5 branch still targets Qt5.

OHOS-specific adaptations:
  - QT_MAJOR_VERSION=5 so the project finds Qt5 (qt5-qtbase/5.15.2).
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS is
    not in the KDE platform list).
  - The native Qt5 cmake config shipped by qt5-qtbase is unusable (its
    Qt5Config.cmake only supports the Qt5Core/Qt5Network/Qt5Gui/Qt5Test/
    Qt5Concurrent per-module configs, not the aggregated Qt5 package that
    find_package(Qt5 ...) expects).  CMakeDeps regenerates a clean Qt5Config
    via `set_property("qt5-qtbase", "cmake_file_name", "Qt5")`.
  - ECM_MODULE_PATH is set explicitly because the project's CMakeLists.txt
    relies on `set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH})`, and ecm is a
    tool_requires (build context) so CMakeDeps does not wire its share/ECM
    tree into the host prefix paths automatically.
  - CMAKE_AUTOMOC_EXECUTABLE / CMAKE_AUTORCC_EXECUTABLE point at the
    qt5-qtbase bin/moc and bin/rcc (CMakeDeps does not export the
    Qt5::moc/Qt5::rcc executable targets).
  - tests/projecttest requires Qt5Widgets which is not shipped by
    qt5-qtbase; the recipe patch makes it optional so configtest and
    persontest still build and run.
  - providertest hits the external OCS endpoint over the network and is
    excluded from ctest (the remaining configtest/persontest run locally).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class Attica5Conan(ConanFile):
    name = "attica5"
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
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = self.conan_data["sources"][self.version]
        get(self, url=source["url"], sha256=source["sha256"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # qt5-qtbase ships per-module cmake configs (Qt5Core, Qt5Network, ...)
        # but no aggregated Qt5Config; find_package(Qt5 COMPONENTS ...) in the
        # project needs one, so CMakeDeps generates a clean Qt5Config.
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["QT_MAJOR_VERSION"] = "5"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["ATTICA_STATIC_BUILD"] = "OFF"
        # HarmonyOS is not mapped to the Linux CMake platform, so
        # CMAKE_SHARED_LIBRARY_SONAME_<lang>_FLAG stays undefined and the
        # produced shared library would have no ELF DT_SONAME (the W3 CI L5
        # soname gate fails).  Mirror the platform-validated expat pattern:
        # keep SONAME emission (relocatable) but skip versioned symlinks,
        # which some OHOS/HMDFS build paths reject.
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        qt5 = self.dependencies["qt5-qtbase"]
        moc_path = os.path.join(qt5.package_folder, "bin", "moc")
        rcc_path = os.path.join(qt5.package_folder, "bin", "rcc")
        if not os.path.isfile(moc_path):
            raise RuntimeError(
                "qt5-qtbase/5.15.2 does not provide the required bin/moc tool"
            )
        if not os.path.isfile(rcc_path):
            raise RuntimeError(
                "qt5-qtbase/5.15.2 does not provide the required bin/rcc tool"
            )
        tc.variables["CMAKE_AUTOMOC_EXECUTABLE"] = moc_path
        tc.variables["CMAKE_AUTORCC_EXECUTABLE"] = rcc_path

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

        tc.generate()

        # CMakeDeps puts ecm's builddir (share/ECM/cmake) only into
        # CMAKE_MODULE_PATH, but the project calls
        # find_package(ECM 5.116.0 NO_MODULE) which needs ECMConfig.cmake on
        # the config-mode search path.  Append the ecm cmake dir to both
        # CMAKE_PREFIX_PATH and CMAKE_MODULE_PATH.
        if ecm:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            if os.path.exists(paths_file):
                with open(paths_file, "a", encoding="utf-8") as f:
                    f.write(
                        'list(PREPEND CMAKE_MODULE_PATH "%s")\n'
                        'list(PREPEND CMAKE_PREFIX_PATH "%s")\n'
                        % (ecm_cmake, ecm_cmake)
                    )

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
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
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
                'ctest --test-dir "{}" --output-on-failure --no-tests=error '
                '-E "^providertest$"'.format(self.build_folder)
            )

    def _prepare_ctest_runtime_links(self):
        # CTest discovers executables in <build>/bin but their libKF5Attica
        # and Qt5 runtime deps live in the build tree / conan package folders.
        # Symlink them next to the test binaries so the linker can resolve.
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
        self.cpp_info.libs = ["KF5Attica"]
