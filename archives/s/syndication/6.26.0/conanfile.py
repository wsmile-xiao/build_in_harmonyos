#!/usr/bin/env python3
"""Conan recipe for syndication 6.26.0 on HarmonyOS PC.

syndication is the KDE Frameworks 6 RSS/Atom/RDF feed parsing library
(libKF6Syndication.so), a Tier 2 functional framework used by feed-reader
frontends (alligator etc.) to parse RSS 2.0, RDF/RSS 1.0 and Atom feeds
through the Syndication::ParserCollection API.

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - KF_SKIP_PO_PROCESSING=ON to skip translation catalog generation for the
    baseline package
  - BUILD_TESTING=ON and ctest execution for the upstream autotests
    (testpersonimpl / syndicationtest / loaderutiltest); syndicationtest is
    data-driven over the 71 upstream feed fixtures (atom 28 + rdf 9 +
    rss2 34)
  - CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG passed explicitly: CMake has no
    Platform/HarmonyOS module so the flag stays unset and libKF6Syndication
    would get no DT_SONAME (kfilemetadata/baloo precedent)
  - C++20 forced via CMAKE_CXX_FLAGS (KDEFrameworkCompilerSettings expects
    C++20; the conan profile pins cppstd=17, kcoreaddons precedent:
    CMAKE_CXX_STANDARD is overridden by variable_watch)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase and the KF6
    packages use cmake_find_mode=none, so CMakeDeps does not add their
    lib/cmake builddirs to CMAKE_PREFIX_PATH
  - QT_ADDITIONAL_PACKAGES_PREFIX_PATH so Qt6 module configs
    (Qt6Xml/Qt6Network/Qt6Test) are found in the qtbase package
  - 0001-lower-kf-dep-version.patch lowers KF_DEP_VERSION 6.26.0 -> 6.18.0
    to match the ohpcd published kcodecs baseline (ECM stays at 6.26.0,
    already published)
  - Dependencies: qtbase/6.11.1 (Qt6 Core/Xml/Network/Test), kcodecs/6.18.0,
    ecm/6.26.0 (ECM, build tool) - all verified published on ohpcd
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class SyndicationConan(ConanFile):
    name = "syndication"
    version = "6.26.0"
    description = "KDE Frameworks 6 - RSS/Atom/RDF feed parsing library"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/syndication"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("kcodecs/6.18.0")

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
        # C++20: KDEFrameworkCompilerSettings expects C++20 and the profile
        # pins cppstd=17; KDECompilerSettings overrides CMAKE_CXX_STANDARD
        # through variable_watch, so the standard must be forced via flags
        # (kcoreaddons/kfilemetadata precedent).
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_CXX_FLAGS"] = "-std=c++20"
        # CMake has no Platform/HarmonyOS module, so UNIX and
        # CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG stay unset and CMake would not
        # pass -Wl,-soname. Provide the flag explicitly so libKF6Syndication
        # gets a DT_SONAME + versioned symlink chain (kfilemetadata/baloo
        # precedent).
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"

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

        # Qt6 module configs (Qt6Xml/Qt6Network/Qt6Test) live in the qtbase
        # package; Qt only searches the prefixes listed in
        # QT_ADDITIONAL_PACKAGES_PREFIX_PATH for module configs (Qt6
        # convention, semicolon-separated).
        qt_prefixes = []
        for dep in list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        ):
            if dep and dep.package_folder:
                qt_prefixes.append(dep.package_folder)
        if qt_prefixes:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(
                qt_prefixes
            )

        # Private build_folder paths.cmake (R49): inject dependency cmake dirs
        # into CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH. qtbase and kcodecs are
        # consumed with cmake_find_mode=none, so CMakeDeps does not generate
        # these paths.
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        deps = list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        )
        for dep in deps:
            if dep and dep.package_folder:
                lines.append(
                    'list(PREPEND CMAKE_PREFIX_PATH "'
                    + dep.package_folder
                    + '/lib/cmake")'
                )
                lines.append(
                    'list(PREPEND CMAKE_LIBRARY_PATH "'
                    + dep.package_folder
                    + '/lib")'
                )
                lines.append(
                    'list(PREPEND CMAKE_INCLUDE_PATH "'
                    + dep.package_folder
                    + '/include")'
                )
        if ecm and ecm.package_folder:
            ecm_cmake = os.path.join(
                ecm.package_folder, "share", "ECM", "cmake"
            )
            lines.append(
                'list(PREPEND CMAKE_MODULE_PATH "' + ecm_cmake + '")'
            )
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH "' + ecm_cmake + '")'
            )
            for rel in ("modules", "find-modules", "kde-modules"):
                lines.append(
                    'list(PREPEND CMAKE_MODULE_PATH "'
                    + os.path.join(ecm.package_folder, "share", "ECM", rel)
                    + '")'
                )
        lines.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append(
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        qtbase = self.dependencies.get("qtbase")
        if qtbase and qtbase.package_folder:
            lines.append(
                'set(CONAN_RUNTIME_LIB_DIRS "'
                + os.path.join(qtbase.package_folder, "lib")
                + '")'
            )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

        tc.generate()

        # ECM KDEInstallDirs runs the qtbase qtpaths host tool during
        # configure (ecm_query_qt -> QT_INSTALL_PREFIX). The sandbox
        # LD_LIBRARY_PATH contains an incompatible libc++_shared.so which
        # shadows the compatible one; prepend /system/lib64 and the qtbase
        # lib dir so the loader resolves the compatible libc++ first
        # (bluez-qt 6.28.0 / kconfig 6.26.0 / baloo 6.28.0 precedent).
        if qtbase and qtbase.package_folder:
            env = Environment()
            env.prepend_path(
                "PATH", os.path.join(qtbase.package_folder, "bin")
            )
            env.prepend_path(
                "LD_LIBRARY_PATH",
                os.path.join(qtbase.package_folder, "lib"),
            )
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            env.vars(self).save_script("conanbuild_qtpaths")

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms are not affected.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._library_runtime_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        if self.settings.os == "OHOS":
            self._run_upstream_tests()

    def _library_runtime_env(self):
        runtime_env = Environment()
        for dep in list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        ):
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins"),
                )
                runtime_env.prepend_path(
                    "QML2_IMPORT_PATH",
                    os.path.join(dep.package_folder, "qml"),
                )
        for rel in ("bin", "lib", "src"):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        runtime_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
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
        test_env.define(
            "XDG_CACHE_HOME", os.path.join(test_home, ".cache")
        )
        test_env.define(
            "XDG_CONFIG_HOME", os.path.join(test_home, ".config")
        )
        test_env.define(
            "XDG_DATA_HOME", os.path.join(test_home, ".local", "share")
        )
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure '
                '--no-tests=error'.format(self.build_folder)
            )

    def package(self):
        cmake = CMake(self)
        with self._library_runtime_env().vars(self).apply():
            cmake.install()

    def package_info(self):
        # The project installs its own KF6SyndicationConfig.cmake with proper
        # dependency tracking (find_dependency on KF6Codecs/Qt6Xml under
        # static builds). Use cmake_find_mode=none so CMakeDeps does not
        # shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6Syndication"]
