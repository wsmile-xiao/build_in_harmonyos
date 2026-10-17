#!/usr/bin/env python3
"""Conan recipe for ki18n5 5.116.0 (KDE Frameworks 5) on HarmonyOS PC.

ki18n5 is the KDE Gettext-based UI text internationalization library
(builds libKF5I18n). The KF5 branch still targets Qt5.

OHOS-specific adaptations (validated on the sibling attica5/5.116.0 and
ki18n 6.x recipes):
  - QT_MAJOR_VERSION=5 so the project finds Qt5 (qt5-qtbase/5.15.2).
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS is
    not in the KDE platform list).
  - BUILD_WITH_QML=ON: qt5-qtdeclarative/5.15.2 is published on ohpcd and its
    Qt5Qml config resolves via CMakeDeps (cmake_file_name Qt5Qml), so the QML
    add-ons (KLocalizedContext, ktranscript) build and the upstream QML
    autotest runs.
  - iso-codes is a requirement: FindIsoCodes resolves via pkg-config and the
    JSON/…mo data is deployed to the Qt test-mode data dir for autotests.
  - KF_SKIP_PO_PROCESSING=ON: skip translation catalog generation.
  - FindLibIntl is satisfied via the published gettext/0.22.5.1 package
    (libintl.h + libintl), CMAKE_INCLUDE_PATH/CMAKE_LIBRARY_PATH point at it.
  - ecm is a tool_requires; ecm/6.26.0 satisfies find_package(ECM 5.116.0)
    (minimum-version semantics, same pattern as attica5/5.116.0).
  - qt5-qtbase ships per-module cmake configs but no aggregated Qt5Config;
    CMakeDeps regenerates one via cmake_file_name "Qt5" (attica5 pattern).
  - CMAKE_AUTOMOC_EXECUTABLE / CMAKE_AUTORCC_EXECUTABLE point at the
    qt5-qtbase bin/moc and bin/rcc (CMakeDeps does not export Qt5::moc/rcc).
  - HarmonyOS is not mapped to the Linux CMake platform, so
    CMAKE_SHARED_LIBRARY_SONAME_<lang>_FLAG is undefined and produced .so
    files would lack DT_SONAME (W3 CI L5 gate). Set the soname flag +
    CMAKE_PLATFORM_NO_VERSIONED_SONAME (expat/attica5 validated pattern).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class Ki18n5Conan(ConanFile):
    name = "ki18n5"
    version = "5.116.0"
    description = "KDE Frameworks 5 - KDE Gettext-based UI text internationalization"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/ki18n"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")
        # QML add-ons (ktranscript, KLocalizedContext) and the upstream QML
        # autotest need Qt5Qml when BUILD_WITH_QML=ON.
        self.requires("qt5-qtdeclarative/5.15.2")
        # libintl is part of gettext; 0.22.5.1 also ships msgfmt, which the
        # ki18n_install upstream autotest needs.
        self.requires("gettext/0.22.5.1")
        # Runtime data dependency (iso_3166/iso_639 JSON + locale .mo) for
        # KCountry/KTimeZone lookups; resolved by the upstream FindIsoCodes
        # module via pkg-config.
        self.requires("iso-codes/4.20.1")

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
        deps.set_property("qt5-qtdeclarative", "cmake_file_name", "Qt5Qml")
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["QT_MAJOR_VERSION"] = "5"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_WITH_QML"] = "ON"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # SONAME emission on OHOS (see module docstring).
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        # ki18n's FindLibIntl looks for libintl.h/libintl. Point it at the
        # published gettext package.
        gettext = self.dependencies.get("gettext")
        if gettext:
            tc.variables["CMAKE_INCLUDE_PATH"] = os.path.join(
                gettext.package_folder, "include")
            tc.variables["CMAKE_LIBRARY_PATH"] = os.path.join(
                gettext.package_folder, "lib")
            # KF5I18nMacros.cmake runs find_package(Gettext); the CMake
            # FindGettext module only probes PATH for the tools, which the
            # conan env does not provide at configure time — pass them
            # explicitly.
            for tool in ("MSGFMT", "MSGMERGE"):
                tool_path = os.path.join(
                    gettext.package_folder, "bin", tool.lower())
                if os.path.isfile(tool_path):
                    tc.variables["GETTEXT_%s_EXECUTABLE" % tool] = tool_path

        # FindIsoCodes resolves iso-codes via pkg-config (pkg_check_modules).
        # The ohpcd package ships the .pc in share/pkgconfig, so export
        # PKG_CONFIG_PATH for the configure step via the conanbuild env.
        isocodes = self.dependencies.get("iso-codes")
        if isocodes:
            pc_dir = os.path.join(
                isocodes.package_folder, "share", "pkgconfig")
            env_pc = Environment()
            env_pc.prepend_path("PKG_CONFIG_PATH", pc_dir)
            env_pc.vars(self).save_script("ki18n5_pkgconfig_isocodes")

        # ECM's CMakeDeps-generated ECMConfig.cmake does not propagate
        # ECM_MODULE_PATH; set it manually so KDE cmake modules
        # (KDEInstallDirs, KDECMakeSettings, ...) are found.  ECM_DIR must be
        # set as a toolchain variable (not appended to the paths file, which
        # CMakeDeps only materializes after tc.generate()).
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_DIR"] = os.path.join(ecm_share, "cmake")
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
                "qt5-qtbase/5.15.2 does not provide the required bin/moc tool"
            )
        if not os.path.isfile(rcc_path):
            raise RuntimeError(
                "qt5-qtbase/5.15.2 does not provide the required bin/rcc tool"
            )
        tc.variables["CMAKE_AUTOMOC_EXECUTABLE"] = moc_path
        tc.variables["CMAKE_AUTORCC_EXECUTABLE"] = rcc_path

        tc.generate()

        # find_package(ECM 5.116.0 NO_MODULE) needs ECMConfig.cmake on the
        # config-mode search path; find_package(Qt5Qml) needs the generators
        # folder (CMakeDeps writes Qt5QmlConfig.cmake there); qtbase's native
        # Qt5Core config needs the qtbase cmake dir.  The toolchain only
        # populates CMAKE_PREFIX_PATH / CMAKE_MODULE_PATH from its else
        # branch when conan_cmakedeps_paths.cmake does NOT exist — classic
        # CMakeDeps never creates that file, so create it here with the
        # entries the else branch would have provided (plus qtbase's).
        extra_paths = []
        if ecm:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            extra_paths.append(
                ('list(PREPEND CMAKE_MODULE_PATH "%s")\n'
                 'list(PREPEND CMAKE_PREFIX_PATH "%s")') % (ecm_cmake, ecm_cmake)
            )
        # The generators folder is where CMakeDeps saves Qt5QmlConfig.cmake;
        # without it find_package(Qt5Qml CONFIG) cannot resolve.
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
        # exist in the conan cache). attica-kf5/5.116.0 validated workaround:
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
                    "PATH", os.path.join(dep.package_folder, "bin")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                runtime_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
                qml_dir = os.path.join(dep.package_folder, "qml")
                if os.path.isdir(qml_dir):
                    runtime_env.prepend_path("QML2_IMPORT_PATH", qml_dir)
                    runtime_env.prepend_path("QML_IMPORT_PATH", qml_dir)
        for dep in self.dependencies.build.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "CMAKE_PREFIX_PATH", dep.package_folder
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
        self._deploy_iso_codes_test_data(test_home)
        self._prepare_ctest_runtime_links()
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def _deploy_iso_codes_test_data(self, test_home):
        # The localedata autotests enable QStandardPaths::setTestModeEnabled(true),
        # which pins GenericDataLocation to <HOME>/.qttest/share regardless of
        # XDG_DATA_HOME/XDG_DATA_DIRS. Deploy the iso-codes JSON databases and
        # the locale catalogs there so the data-driven tests can resolve them.
        isocodes = self.dependencies.get("iso-codes")
        if not isocodes:
            return
        pkg = isocodes.package_folder
        qttest_share = os.path.join(test_home, ".qttest", "share")
        data_root = os.path.join(pkg, "share")
        pairs = [
            ("iso-codes/json", "iso-codes/json"),
            ("locale", "locale"),
        ]
        for src_rel, dst_rel in pairs:
            src = os.path.join(data_root, src_rel)
            if not os.path.exists(src):
                self.output.warn(
                    "iso-codes data missing in package: {}".format(src)
                )
                continue
            dst = os.path.join(qttest_share, dst_rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
        self.output.info(
            "Deployed iso-codes test data to {}".format(qttest_share)
        )

    def _prepare_ctest_runtime_links(self):
        # CTest discovers executables in <build>/bin; their libKF5I18n and
        # Qt5 runtime deps live in the build tree / conan package folders.
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
        # The project installs its own KF5I18nConfig.cmake with proper
        # dependency tracking (find_dependency on Qt5Core). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5I18n"]
