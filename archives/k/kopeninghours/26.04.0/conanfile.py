#!/usr/bin/env python3
"""Conan recipe for kopeninghours 26.04.0 on HarmonyOS PC.

kopeninghours is a KDE library (libKOpeningHours.so) that parses and
evaluates OpenStreetMap opening hours expressions (e.g. "Mo-Fr 08:00-12:00"),
including "variable time" references such as "sunrise"/"sunset" (computed
via kholidays' astronomical code) and public-holiday references ("PH").

Build system: CMake. The parser/scanner (openinghoursparser.y /
openinghourslexer.l) are generated at build time with bison + flex.

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list), kconfig/kdbusaddons/kholidays precedent
  - BUILD_WITH_QT6=ON: ECM's QtVersionOption.cmake defaults to Qt5 when
    ECM_GLOBAL_FIND_VERSION is unset (ECM 6.x does not define it); kopeninghours
    still contains the legacy Qt5/Qt6 dual-path CMake code, so the Qt6 code
    path must be selected explicitly
  - ECM_VERSION=6.28.0: the top-level CMakeLists.txt does
    `if (ECM_VERSION VERSION_GREATER_EQUAL 5.91) ... else set(QT_MAJOR_VERSION 5)`
    ECM 6.28's ECMConfig.cmake does not define ECM_VERSION, so the legacy
    branch would force Qt5; pin ECM_VERSION to satisfy the check
  - GETTEXT_MSGFMT_EXECUTABLE is set explicitly from the gettext package
    (transitive dep of ki18n): the upstream `ki18n_install(po)` macro runs
    msgfmt at build time to produce .mo catalogs; OHOS has no system gettext
  - bison/3.8.2's pkgdatadir is compiled as /share/bison (built with
    --prefix=), so BISON_PKGDATADIR + M4 must point into the conan packages
    (dawg/libidl precedent)
  - tzdata/2026.3 + TZDIR/QT_ZONEINFO: the autotests resolve named time
    zones (evaluatetest sets TZ=Europe/Berlin, iterationtest TZ=Pacific/Auckland,
    sunrise/sunset computations) and OHOS ships no /usr/share/zoneinfo;
    kcalendarcore precedent (evaluatetest goes from 128+4 FAIL to 132/132,
    iterationtest from a sunrise crash to 29/29 with TZDIR set)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KopeninghoursConan(ConanFile):
    name = "kopeninghours"
    version = "26.04.0"
    description = "KDE library to parse and evaluate OpenStreetMap opening hours expressions"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/libraries/kopeninghours"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6::Core is the public link dependency (KOpeningHours target).
        # qtbase/6.11.1 is the published binary, same as kholidays/ki18n.
        self.requires("qtbase/6.11.1")
        # KF6::I18n: private link dependency + ki18n_install(po) CMake macros.
        self.requires("ki18n/6.18.0.1")
        # KF6::Holidays: private link dependency for variable-time evaluation
        # (sunrise/sunset) and the iterationtest autotest.
        self.requires("kholidays/6.28.0")
        # Upstream autotests resolve named timezones (Europe/Berlin,
        # Pacific/Auckland) and the OHOS system has no /usr/share/zoneinfo,
        # so a TZif database is required at test time (TZDIR + QT_ZONEINFO).
        self.requires("tzdata/2026.3")

    def build_requirements(self):
        # ECM is REQUIRED upstream (find_package(ECM 5.44)); 6.28.0 is the
        # published base used by the other KF6 packages.
        self.tool_requires("extra-cmake-modules/6.28.0")
        # Parser/scanner are generated at build time from
        # openinghoursparser.y / openinghourslexer.l.
        self.tool_requires("flex/2.6.4.2")
        self.tool_requires("bison/3.8.2")
        # bison expands its m4sugar macro library through the m4 binary.
        self.tool_requires("m4/1.4.19")

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
        # ECM's QtVersionOption selects Qt5 unless explicitly told otherwise
        # (ECM_GLOBAL_FIND_VERSION is unset in ECM 6.28), and the legacy
        # `if (ECM_VERSION VERSION_GREATER_EQUAL 5.91)` in the top-level
        # CMakeLists would also force Qt5 — pin both to take the Qt6 path.
        tc.variables["BUILD_WITH_QT6"] = "ON"
        tc.variables["ECM_VERSION"] = "6.28.0"

        # ki18n_install(po) runs msgfmt at build time; point CMake at the
        # gettext msgfmt binary (transitive dep of ki18n/6.18.0.1).
        gettext = self.dependencies.get("gettext")
        if gettext and gettext.package_folder:
            msgfmt = os.path.join(gettext.package_folder, "bin", "msgfmt")
            if os.path.exists(msgfmt):
                tc.variables["GETTEXT_MSGFMT_EXECUTABLE"] = msgfmt
            else:
                raise ConanException(
                    "gettext package has no bin/msgfmt: {}".format(msgfmt)
                )

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, ECMAddTests,
        # ECMGenerateHeaders, ECMSetupVersion, ...) are found.
        ecm = self.dependencies.build.get("extra-cmake-modules")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qtbase = self.dependencies.get("qtbase")
        kholidays = self.dependencies.get("kholidays")
        ki18n = self.dependencies.get("ki18n")
        if qtbase:
            qt_pkg = qtbase.package_folder
            # qtbase uses cmake_find_mode=none -> CMakeDeps does not generate
            # conan_cmakedeps_paths.cmake. Create it manually so the toolchain
            # adds qtbase's cmake dirs to CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH.
            # (The generated toolchain's find_paths block is skipped when this
            # file exists, so the kholidays/ki18n/ECM cmake dirs must be added
            # here explicitly as well.)
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            for dep in (kholidays, ki18n):
                if dep and dep.package_folder:
                    dep_cmake = os.path.join(dep.package_folder, "lib", "cmake")
                    lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{dep_cmake}")')
                    lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH '
                                 f'"{os.path.join(dep.package_folder, "lib")}")')
            if ecm:
                ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
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
            lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
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
            # libc++ first (kholidays/bluez-qt precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        # bison's pkgdatadir is compiled as /share/bison (built with
        # --prefix=); point BISON_PKGDATADIR at the real data and M4 at the
        # m4 tool package so grammar generation works (dawg precedent).
        bison = self.dependencies.build.get("bison")
        m4 = self.dependencies.build.get("m4")
        if bison:
            bison_pkgdata = os.path.join(bison.package_folder, "share", "bison")
            if not os.path.isdir(bison_pkgdata):
                raise ConanException(
                    "bison package has no share/bison dir: {}".format(bison_pkgdata)
                )
            build_env.define_path("BISON_PKGDATADIR", bison_pkgdata)
        if m4:
            m4_bin = os.path.join(m4.package_folder, "bin", "m4")
            build_env.define_path("M4", m4_bin)
        return build_env

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        tzdata = self.dependencies.get("tzdata")
        if tzdata and tzdata.package_folder:
            zoneinfo = os.path.join(
                tzdata.package_folder,
                "lib",
                "python3.12",
                "site-packages",
                "tzdata",
                "zoneinfo",
            )
            if os.path.isdir(zoneinfo):
                test_env.define("TZDIR", zoneinfo)
                test_env.define("QT_ZONEINFO", zoneinfo)
            else:
                raise ConanException("tzdata package has no zoneinfo: {}".format(zoneinfo))
        test_env.define("TZ", "UTC")
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
            # Upstream autotests registered by autotests/CMakeLists.txt:
            # parsertest, jsonldtest, intervaltest, eastertest, evaluatetest,
            # iterationtest (links KF6::Holidays), intervalmodeltest.
            # The test binaries link libKOpeningHours.so via a relative
            # NEEDED entry (../bin/...), which the loader resolves from the
            # ctest working directory (the autotests/ build dir).
            self.run(
                'ctest --test-dir "{}" --output-on-failure '
                '--no-tests=error --timeout 300'.format(self.build_folder)
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KOpeningHoursConfig.cmake with proper
        # dependency tracking (find_dependency on Qt6Core). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KOpeningHours"]
        self.cpp_info.resdirs = ["share"]
