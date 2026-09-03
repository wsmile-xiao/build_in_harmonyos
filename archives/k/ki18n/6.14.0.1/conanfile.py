#!/usr/bin/env python3
"""Conan recipe for ki18n 6.14.0.1 on HarmonyOS PC.

Revision 6.14.0.1 (fix task contrib-3768, platform branch fix/ki18n-6.14.0):
ki18n 6.14.0 was published with BUILD_WITH_QML=OFF (qtdeclarative was not
published at the time) and BUILD_TESTING=OFF, matching the first Akonadi
KF baseline. qtdeclarative/6.11.1 is published now and the 6.18.0.1 fix
already proved the QML add-on + upstream CTest path works on OHOS, so this
revision backports the same fix to 6.14.0 (R37 version bump: the artifact
registry does not host multiple revisions of the same version).

Unlocked in this revision (same set as 6.18.0.1):
  - BUILD_WITH_QML=ON: the QML i18n add-on (KF6I18nQml: KLocalizedContext/
    KLocalizedQmlContext + localedata QML plugin) is built and installed.
  - BUILD_TESTING=ON: upstream autotests run via ctest during the build.
  - KF_SKIP_PO_PROCESSING=ON: translation catalog generation is skipped.

ki18n is a KDE Frameworks 6 internationalization library
(libKF6I18n.so).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - BUILD_WITH_QML=ON: qtdeclarative/6.11.1 (Qt6 Qml) is published; the QML
    add-on (KF6::I18nQml) is required by KF6NewStuff widgets/dialogs
  - KF_SKIP_PO_PROCESSING=ON: skip building translation catalogs for the
    initial Akonadi KF baseline
  - BUILD_TESTING=ON and ctest execution for upstream autotests available in
    the current feature set
  - Dependencies: qtbase/6.11.1 (Qt6Core/Qt6Widgets), ecm/6.26.0 (ECM)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class Ki18nConan(ConanFile):
    name = "ki18n"
    version = "6.14.0.1"
    description = "KDE Frameworks 6 - KDE Gettext-based UI text internationalization"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/ki18n"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        # QML i18n add-on (BUILD_WITH_QML=ON) compiles against Qt6::Qml,
        # provided by the published qtdeclarative split package.
        self.requires("qtdeclarative/6.11.1")
        # libintl is part of gettext; 0.22.5.1 also ships msgfmt, which the
        # ki18n_install upstream autotest needs.
        self.requires("gettext/0.22.5.1")

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
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # Qt6 Qml is available via qtdeclarative/6.11.1 now: ship the QML
        # add-on (KF6I18nQml) needed by KF6NewStuff.
        tc.variables["BUILD_WITH_QML"] = "ON"
        # Akonadi needs KF6::I18n, not the translated catalog payload.
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"

        # ki18n's FindLibIntl looks for libintl.h/libintl.a. Use the
        # published gettext package (libintl is part of gettext) to provide
        # them, so find_path/find_library succeed on any environment.
        gettext = self.dependencies.get("gettext")
        if gettext:
            tc.variables["CMAKE_INCLUDE_PATH"] = os.path.join(
                gettext.package_folder, "include")
            tc.variables["CMAKE_LIBRARY_PATH"] = os.path.join(
                gettext.package_folder, "lib")

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, etc.) are found.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        # Qt6 split-package component resolution (Qt6Qml lives in the
        # qtdeclarative package): qtbase's Qt6Config only finds it through
        # QT_ADDITIONAL_PACKAGES_PREFIX_PATH, CMAKE_PREFIX_PATH alone is not
        # enough (verified on ktextwidgets/knewstuff pipelines).
        qt_extra = [
            dep.package_folder for dep in self.dependencies.values()
            if dep and dep.package_folder
            and os.path.isdir(os.path.join(dep.package_folder, "lib", "cmake"))
            and any(n.startswith("Qt6") for n in os.listdir(
                os.path.join(dep.package_folder, "lib", "cmake")))
        ]
        if qt_extra:
            tc.cache_variables[
                "QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)

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
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms (e.g. BSD) are not affected.
        if self.settings.os == "OHOS":
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
                    "CMAKE_PREFIX_PATH", dep.package_folder
                )
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "PATH", os.path.join(dep.package_folder, "bin")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                # QML runtime modules: qtdeclarative ships qmldir trees
                # under <pkg>/qml/; without these paths on QML2_IMPORT_PATH
                # the engine reports `module "QtQml" is not installed`.
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
        self._prepare_ctest_runtime_links()
        excluded_tests = (
            # ohpcd does not currently provide iso-codes; these tests require
            # iso_3166 JSON data via the optional upstream IsoCodes runtime.
            "kcatalogtest",
            "kcountrytest",
            "kcountrysubdivisiontest",
            "ktimezonetest",
        )
        exclude_re = "^({})$".format("|".join(excluded_tests))
        self.output.info(
            "Excluding upstream tests requiring unavailable OHOS iso-codes data: {}".format(
                ", ".join(excluded_tests)
            )
        )
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error -E "{}"'.format(
                    self.build_folder, exclude_re
                )
            )

    def _prepare_ctest_runtime_links(self):
        compatibility_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, "bin")
        )
        os.makedirs(compatibility_bin, exist_ok=True)
        for lib_name in ("libKF6I18n.so", "libKF6I18nLocaleData.so",
                         "libKF6I18nQml.so", "libKF6LocaleDataQml.so"):
            src = os.path.join(self.build_folder, "bin", lib_name)
            dst = os.path.join(compatibility_bin, lib_name)
            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    os.symlink(src, dst)
                except OSError:
                    shutil.copy2(src, dst)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KF6I18nConfig.cmake with proper
        # dependency tracking (find_dependency on Qt6Core). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6I18n"]
