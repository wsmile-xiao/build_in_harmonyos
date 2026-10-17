#!/usr/bin/env python3
"""Conan recipe for kholidays 6.28.0 on HarmonyOS PC.

kholidays is a KDE Frameworks 6 library (libKF6Holidays.so) that computes
holiday calendars (holiday region data + a plan-language parser) and
astronomical events: sunrise/sunset (SunRiseSet), solar events for a given
location and date (SunEvents, used by Plasma knighttime for the dark-light
schedule), lunar phases, zodiac signs and astro seasons.

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list), same as kconfig/kdbusaddons precedents
  - BUILD_TESTING=ON and ctest execution for the 7 upstream autotests
    (testlunar, testseasons, testsunriseset, testzodiac,
    testholidayregion, testsunevents, testcategories)
  - Parser generation: upstream generates the holiday plan parser with
    bison + flex at build time; both are declared as tool_requires
    (bison/3.8.2, flex/2.6.4, m4/1.4.19, acpica-unix precedent)
  - Dependencies: qtbase/6.11.1 (Qt6::Core), qtdeclarative/6.11.1
    (Qt6::Qml for the org.kde.kholidays QML plugin),
    extra-cmake-modules/6.29.0 (ECM >= 6.28.0 required upstream) and
    qt6linguisttools/6.11.1 for the poqm translation step
    (ecm_install_po_files_as_qm, kdbusaddons precedent)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KholidaysConan(ConanFile):
    name = "kholidays"
    version = "6.28.0"
    description = "KDE Frameworks 6 - Holiday calendars and astronomical events (sunrise/sunset, lunar phases, zodiac)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kholidays"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6::Core is the public link dependency (KF6Holidays target).
        # qtbase/6.11.1 is the published binary (r04 consumption gate).
        self.requires("qtbase/6.11.1")
        # The org.kde.kholidays QML plugin links Qt6::Qml, provided by the
        # published qtdeclarative/6.11.1 package.
        self.requires("qtdeclarative/6.11.1")

    def build_requirements(self):
        # ECM >= 6.28.0 is REQUIRED upstream (find_package(ECM 6.28.0)).
        # extra-cmake-modules/6.29.0 is the published ECM base (ecm/6.26.0
        # is too old for this release).
        self.tool_requires("extra-cmake-modules/6.29.0")
        # Qt6LinguistTools is a build-time tool set (lrelease/lconvert +
        # Qt6::LinguistTools CMake module) required by ECMPoQmTools for the
        # upstream poqm translation step (kdbusaddons precedent).
        self.tool_requires("qt6linguisttools/6.11.1")
        # The holiday plan parser is generated at build time from
        # holidayparserplan.ypp / holidayscannerplan.lpp (acpica-unix
        # precedent for bison/flex/m4 as Conan tool requirements).
        self.tool_requires("bison/3.8.2")
        self.tool_requires("flex/2.6.4")
        self.tool_requires("m4/1.4.19")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # The upstream sources use C++20 features (std::ranges::none_of in
        # holidayregion.cpp) while the repo profile pins cppstd=17. Remove
        # the conan cppstd block so CMAKE_CXX_STANDARD=20 is honored
        # (baloo 6.28.0 / kcoreaddons precedent).
        tc.blocks.remove("cppstd")
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, ECMQmlModule,
        # ECMPoQmTools, ECMGenerateQDoc, ...) are found.
        ecm = self.dependencies.build.get("extra-cmake-modules")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qtbase = self.dependencies.get("qtbase")
        qtdeclarative = self.dependencies.get("qtdeclarative")
        if qtbase:
            qt_pkg = qtbase.package_folder
            # qtbase uses cmake_find_mode=none -> CMakeDeps does not generate
            # conan_cmakedeps_paths.cmake. Create it manually so the toolchain
            # adds qtbase's cmake dirs to CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH.
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if qtdeclarative:
                qml_pkg = qtdeclarative.package_folder
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qml_pkg}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qml_pkg}/lib")')
            ltt = self.dependencies.build.get("qt6linguisttools")
            if ltt:
                ltt_pkg = ltt.package_folder
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ltt_pkg}/lib/cmake")')
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{ltt_pkg}/lib/cmake/Qt6LinguistTools")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_MODULE_PATH '
                    f'"{ltt_pkg}/lib/cmake/Qt6LinguistTools")'
                )
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{ltt_pkg}/lib")')
                # ECMPoQmTools calls find_package(Qt6 COMPONENTS LinguistTools)
                # which resolves via qtbase's Qt6Config.cmake: add the
                # qt6linguisttools package root as an additional Qt prefix.
                ltt_prefixes = [ltt_pkg]
                if qtdeclarative:
                    qml_prefixes = [qtdeclarative.package_folder]
                else:
                    qml_prefixes = []
                tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(
                    qml_prefixes + ltt_prefixes
                )
                lines.append(
                    'set(QT_ADDITIONAL_PACKAGES_PREFIX_PATH '
                    f'"{";".join(qml_prefixes + ltt_prefixes)}" CACHE STRING '
                    '"Additional directories where find(Qt6 ...) components '
                    'are searched" FORCE)'
                )
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
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

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
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
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            # ECM KDEInstallDirs6 runs the qtbase qtpaths host tool during
            # configure (ecm_query_qt -> QT_INSTALL_PREFIX). The sandbox
            # LD_LIBRARY_PATH contains an incompatible libc++_shared.so under
            # /data/storage/el1/bundle/libs/arm64 which shadows the compatible
            # one; prepend /system/lib64 so the loader resolves the compatible
            # libc++ first (bluez-qt 6.28.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_env.define("TZ", "UTC")
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
            # Run the upstream ctest suite: 7 autotests are registered by
            # autotests/CMakeLists.txt (testlunar, testseasons,
            # testsunriseset, testzodiac, testholidayregion, testsunevents,
            # testcategories). They are plain computation tests over the
            # bundled holiday data and astronomy code and need no display.
            self.run(
                'ctest --test-dir "{}" --output-on-failure '
                '--no-tests=error --timeout 300'.format(self.build_folder)
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KF6HolidaysConfig.cmake with proper
        # dependency tracking (find_dependency on Qt6Core). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6Holidays"]
        self.cpp_info.resdirs = ["share"]
