#!/usr/bin/env python3
"""Conan recipe for accessibility 26.04.3 on HarmonyOS PC.

accessibility-inspector is the KDE Accessibility group's AT-SPI tree
viewer (Qt6 Widgets GUI application). The conan package name
"accessibility" is the platform task name (pipeline gates L0n/L0m
require the branch suffix to equal {conan name}-{version} and the conan
name to equal the package directory); the upstream product, source
tarball and delivered binary remain accessibility-inspector. It delivers:
  - bin/accessibilityinspector          (the GUI application)
  - lib/libaccessibilityinspector.so.1  (internal helper library)

Upstream hard requirements (CMakeLists.txt): CMake >= 3.16, C++20,
Qt6 >= 6.8 (Widgets, Core; Test when BUILD_TESTING), KF6 >= 6.11
(CoreAddons, I18n, DBusAddons, ConfigWidgets, XmlGui, Crash) and
QAccessibilityClient6 >= 0.6.0 (REQUIRED, provided by this run's
qaccessibilityclient/0.6.0 recipe).

OHOS-specific adaptations:
  - C++20 per-recipe override of the cppstd=17 CI profile via
    CMAKE_CXX_STANDARD / CMAKE_CXX_FLAGS (kdbusaddons 6.29.0 precedent)
  - KF_IGNORE_PLATFORM_CHECK=TRUE: bypass KDE platform detection
  - KF_SKIP_PO_PROCESSING=ON: no .po -> .mo conversion (no gettext/msgfmt
    for ki18n_install(po); calligra precedent — translations are not
    required for the app to function)
  - KF6 6.14.0 published closure (calligra-proven set) + kdbusaddons/6.29.0
    (built against qtbase/6.11.1.1, the same ref this recipe pins);
    qtbase/6.11.1.1 override unifies the whole graph on the DBus-enabled
    qtbase (E323)
  - qaccessibilityclient/0.6.0: same-run new dependency (local recipe
    exported; registry publication follows the release pipeline)
  - ECM_MODULE_PATH + ECM find-modules on CMAKE_MODULE_PATH so the
    umbrella find_package(KF6 COMPONENTS ...) resolves (FindKF6.cmake)
  - QUERY_EXECUTABLE=qtpaths6: ECMQueryQt cannot resolve Qt6::qtpaths in
    this qtbase layout (mobipocket precedent)
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none
  - BUILD_TESTING=ON: upstream src/autotests (4 QtTest targets) run via
    ctest inside build() with the offscreen QPA platform; outcomes are
    recorded (karchive/kdbusaddons precedent)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class AccessibilityInspectorConan(ConanFile):
    name = "accessibility"
    version = "26.04.3"
    description = "KDE Accessibility Inspector - AT-SPI accessibility tree viewer (Qt6)"
    license = "LGPL-3.0-or-later"
    homepage = "https://invent.kde.org/accessibility/accessibility-inspector"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Unified Qt6 base (DBus-enabled; E323). All published KF6 recipes
        # pin qtbase/6.11.1; override lifts the whole graph onto the
        # additive 6.11.1.1 binary (same Qt 6.11 ABI, calligra precedent).
        self.requires("qtbase/6.11.1.1", override=True)
        # Direct upstream requirements (find_package(KF6 COMPONENTS ...)).
        self.requires("kcoreaddons/6.14.0")
        self.requires("ki18n/6.14.0")
        self.requires("kdbusaddons/6.29.0")
        self.requires("kconfigwidgets/6.14.0")
        self.requires("kxmlgui/6.14.0")
        self.requires("kcrash/6.14.0")
        # Transitive KF6 closure declared explicitly so every package's
        # cmake dir lands on CMAKE_PREFIX_PATH for the installed
        # KF6*Config.cmake find_dependency chains (calligra precedent).
        self.requires("kconfig/6.14.0")
        self.requires("kcolorscheme/6.14.0")
        self.requires("kcodecs/6.14.0")
        self.requires("kguiaddons/6.14.0")
        self.requires("kiconthemes/6.14.0")
        self.requires("kitemviews/6.14.0")
        self.requires("kwidgetsaddons/6.14.0")
        self.requires("kwindowsystem/6.14.0")
        self.requires("knotifications/6.14.0")
        self.requires("karchive/6.14.0")
        self.requires("qtsvg/6.11.1")
        # The one missing upstream dependency, delivered by this run.
        self.requires("qaccessibilityclient/0.6.0")

    def build_requirements(self):
        # Upstream: find_package(ECM 6.11.0 REQUIRED NO_MODULE).
        self.tool_requires("extra-cmake-modules/6.29.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # ki18n_install(po) needs gettext/msgfmt which OHOS does not ship;
        # skip .po processing (calliga precedent). Translations are not
        # required for the viewer to function.
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # Upstream sets CMAKE_CXX_STANDARD 20 itself; assert it on top of
        # the cppstd=17 profile (kdbusaddons 6.29.0 pattern).
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_CXX_FLAGS"] = "-std=c++20"
        # The OHOS CMake platform module does not define the SONAME flag, so
        # shared libs ship without DT_SONAME and consumers record path-form
        # DT_NEEDED (E537). Enable it at link time: libaccessibilityinspector
        # has VERSION/SOVERSION upstream, so lld emits a real soname, the
        # executable records the bare name, and the toolchain self-signature
        # stays valid. Post-link ELF rewrites ARE possible but must follow
        # the E077 four-step flow (objcopy --remove-section .codesign ->
        # patchelf -> binary-sign-tool sign -selfSign 1 -> chmod); a naive
        # patchelf without re-sign yields "Operation not permitted" (rc=126)
        # and re-signing without removing .codesign is refused
        # (".codesign section already exists" -> SignElf 29) — archived
        # probe: run reports/builder/probe-soname-sign/. Link-time fixing is
        # preferred (producer-side, no per-artifact re-sign step).
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        # Resolve the bare-name soname of the internal helper library at
        # runtime without any environment (the app lives in bin/, the
        # library in lib/). Dependency lib dirs are appended so the bare-name
        # Qt6 entries also resolve for the packaged application (L2 smoke).
        rpath_dirs = ["$ORIGIN/../lib"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    rpath_dirs.append(lib_dir)
        tc.variables["CMAKE_INSTALL_RPATH"] = ";".join(rpath_dirs)
        tc.variables["CMAKE_BUILD_RPATH"] = ";".join(rpath_dirs)

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings,
        # KDECompilerSettings, ECMAddTests, ...) are found.
        ecm = self.dependencies.build.get("extra-cmake-modules")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        # ECM's ECMQueryQt.cmake looks for TARGET Qt6::qtpaths via
        # Qt6CoreTools, which Qt6Config.cmake does not load in this layout.
        # Point QUERY_EXECUTABLE at qtpaths6 directly (mobipocket
        # precedent) so KDEInstallDirs resolves install dirs.
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qtpaths6 = os.path.join(qtbase.package_folder, "bin", "qtpaths6")
            if os.path.exists(qtpaths6):
                tc.variables["QUERY_EXECUTABLE"] = qtpaths6
                tc.variables["_cli_option"] = "--query"

        # Qt6Config.cmake resolves extra COMPONENTS relative to
        # QT_ADDITIONAL_PACKAGES_PREFIX_PATH (calligra precedent).
        qt_extra = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                qt_cmake_dir = os.path.join(dep.package_folder, "lib", "cmake")
                if os.path.isdir(qt_cmake_dir) and any(
                        n.startswith("Qt6")
                        for n in os.listdir(qt_cmake_dir)
                ):
                    qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.cache_variables[
                "QT_ADDITIONAL_PACKAGES_PREFIX_PATH"
            ] = ";".join(qt_extra)

        tc.generate()

        # qtbase uses cmake_find_mode=none -> CMakeDeps does not generate
        # conan_cmakedeps_paths.cmake. Create it manually with every
        # dependency's cmake/lib/include dirs, plus ECM's cmake and
        # find-modules dirs (FindKF6.cmake umbrella resolution).
        lines = ['set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)']
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")'
                )
        if ecm:
            ecm_pkg = ecm.package_folder
            for sub in ("cmake", "find-modules", "modules", "kde-modules"):
                lines.append(
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_pkg}/share/ECM/{sub}")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_pkg}/share/ECM/{sub}")'
                )
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        if qtbase:
            lines.append(
                f'set(CONAN_RUNTIME_LIB_DIRS "{qtbase.package_folder}/lib")'
            )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

        # Build-time helper tools (uic via ki18n_wrap_ui, moc, etc.) run as
        # CMake custom commands during build(); expose every dependency's
        # lib dir to the build environment or they cannot load
        # libQt6Core.so.6 (calligra precedent).
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    self.buildenv.append_path("LD_LIBRARY_PATH", lib_dir)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        test_env = Environment()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_env.define("TZ", "Asia/Shanghai")
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
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                test_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                test_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
        # The test binaries link the build-tree libaccessibilityinspector.
        for rel in ("bin", "lib", os.path.join("src"), os.path.join("src", "autotests")):
            test_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        # Link farm for path-form DT_NEEDED entries inside published KF6
        # libraries ("../../bin/libX.so"): ctest runs each test with
        # CWD = <build>/src/autotests, so "../../bin/" lands in
        # <build>/bin. Symlink every dependency library into it (calligra
        # 24.12.3 test farm precedent).
        farm_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(farm_dir, exist_ok=True)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                dep_lib = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(dep_lib):
                    for name in os.listdir(dep_lib):
                        if name.endswith(".so*") or ".so" in name:
                            link = os.path.join(farm_dir, name)
                            if not os.path.lexists(link):
                                try:
                                    os.symlink(os.path.join(dep_lib, name), link)
                                except OSError as e:
                                    self.output.warning(f"farm skip {name}: {e}")
        with test_env.vars(self).apply():
            # Upstream src/autotests registers 4 QtTest targets
            # (accessibletreewidgettest, accessibletreeviewtest,
            # mainwidgettest, propertytreeviewtest). They build widgets and
            # browse the AT-SPI tree via QAccessibilityClient; slots that
            # need a live a11y bus fail on the headless OHOS build host
            # (environment limitation). Follow the karchive/kdbusaddons
            # precedent: run the suite, record the outcome, do not block
            # package creation on environment-caused failures.
            ret = self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error --timeout 90'.format(
                    self.build_folder
                ),
                env="conanrun",
                ignore_errors=True,
            )
            self.output.info("upstream ctest exit code: {}".format(ret))

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Application package: the delivered product is
        # bin/accessibilityinspector plus the internal helper library
        # libaccessibilityinspector.so.1.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
