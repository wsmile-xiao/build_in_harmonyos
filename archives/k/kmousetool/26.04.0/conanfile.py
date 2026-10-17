#!/usr/bin/env python3
"""Conan recipe for kmousetool 26.04.0 (aarch64-linux-ohos).

KDE accessibility auto-click tool (KDE release-service, Qt6 Widgets app).

OHOS-specific adaptations (accessibility/26.04.3 blueprint):
  - qtbase/6.11.1.1 override: whole graph unified on the DBus-enabled
    additive binary (calligra/accessibility precedent)
  - kiconthemes/6.18.0.1 + karchive/6.18.0 overrides: the 6.18.0/6.19.0
    recipes' binaries were never published (and their upstream ctest fails
    under musl); R36 requires every graph binary to be published
  - extra-cmake-modules/6.29.0 override + tool_require: ECM 6.19.0 binary
    missing and does not build from source (ECMQueryQt/qtpaths)
  - KF_IGNORE_PLATFORM_CHECK=TRUE (OHOS not in KDE platform list)
  - KF_SKIP_PO_PROCESSING=ON: no gettext/msgfmt on OHOS
  - QUERY_EXECUTABLE=qtpaths6: ECMQueryQt cannot resolve Qt6::qtpaths in
    this layout (mobipocket/accessibility precedent)
  - conan_cmakedeps_paths.cmake written manually: qtbase uses
    cmake_find_mode=none, so CMakeDeps does not generate it
  - upstream CMakeLists requires libXt (Intrinsic.h) but no Xt symbol is
    used anywhere in the sources; the Xt check is removed by patch and the
    real dependency is libxtst (XTest API) + libx11 (via libxtst)
  - upstream ships no tests; R51 self-authored test_package provides the
    verification (ELF/aarch64 assertions + offscreen smoke run)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KMouseToolConan(ConanFile):
    name = "kmousetool"
    version = "26.04.0"
    description = "KDE mouse manipulation tool for accessibility (auto-click)"
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/accessibility/kmousetool"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("kde", "accessibility", "mouse", "ohos")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Unified Qt6 base (DBus-enabled; accessibility/calligra precedent).
        self.requires("qtbase/6.11.1.1", override=True)
        self.requires("qtmultimedia/6.11.1")
        # Direct upstream requirements (find_package(KF6 COMPONENTS ...)).
        self.requires("kconfig/6.18.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("kcrash/6.18.0")
        self.requires("kdbusaddons/6.29.0")
        self.requires("ki18n/6.18.0")
        self.requires("kiconthemes/6.18.0.1", override=True)
        self.requires("kwidgetsaddons/6.18.0")
        self.requires("kxmlgui/6.18.0")
        # KStatusNotifierItem (kmousetool.cpp: KStatusNotifierItem base class).
        self.requires("statusnotifieritem/6.26.0")
        # X11 closure actually used by the sources: XTest API (libxtst).
        # libx11 comes transitively from libxtst (transitive_headers +
        # transitive_libs) providing Xlib.h/XOpenDisplay; a direct libx11
        # pin would conflict with libxtst's pinned libx11/6.4.0.
        self.requires("libxtst/1.2.5")
        # Transitive KF6 closure declared explicitly so every package's
        # cmake dir lands on CMAKE_PREFIX_PATH for the installed
        # KF6*Config.cmake find_dependency chains (calligra precedent).
        self.requires("karchive/6.18.0", override=True)
        self.requires("kcodecs/6.18.0")
        self.requires("kcolorscheme/6.18.0")
        self.requires("kguiaddons/6.18.0")
        self.requires("kitemviews/6.18.0")
        self.requires("kwindowsystem/6.18.0")

    def build_requirements(self):
        # Upstream: find_package(ECM REQUIRED NO_MODULE).
        self.tool_requires("extra-cmake-modules/6.29.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake (4.1) has no HarmonyOS platform module: without this the
        # system name stays "HarmonyOS", UNIX is FALSE, and FindX11 (and
        # every other if(UNIX)-guarded module) silently skips all searches
        # (ableton-link/abcmidi precedent, E092).
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # ki18n_install(po) needs gettext/msgmsg which OHOS does not ship.
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated one does not. Set it manually so KDE cmake
        # modules (KDEInstallDirs, KDECMakeSettings, ...) are found.
        ecm = self.dependencies.build.get("extra-cmake-modules")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        # ECMQueryQt.cmake looks for TARGET Qt6::qtpaths via Qt6CoreTools,
        # which Qt6Config.cmake does not load in this layout. Point
        # QUERY_EXECUTABLE at qtpaths6 directly (mobipocket precedent).
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qtpaths6 = os.path.join(qtbase.package_folder, "bin", "qtpaths6")
            if os.path.exists(qtpaths6):
                tc.variables["QUERY_EXECUTABLE"] = qtpaths6
                tc.variables["_cli_option"] = "--query"

        # Runtime rpath: resolve bare-name Qt6/KF6/libX11 entries of the
        # installed app without any environment (accessibility precedent).
        rpath_dirs = ["$ORIGIN"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    rpath_dirs.append(lib_dir)
        tc.variables["CMAKE_INSTALL_RPATH"] = ";".join(rpath_dirs)
        tc.variables["CMAKE_BUILD_RPATH"] = ";".join(rpath_dirs)

        # Qt6Config.cmake resolves extra COMPONENTS (Multimedia, Svg, ...)
        # relative to QT_ADDITIONAL_PACKAGES_PREFIX_PATH (calligra precedent).
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
                # Package ROOT on CMAKE_PREFIX_PATH: config search resolves
                # <root>/lib/cmake, and prefix-based modules (FindX11
                # searches <prefix>/include, <prefix>/lib) resolve too.
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}")'
                )
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

        # Build-time helper tools (uic/moc/kcm-wrapper) run as CMake custom
        # commands during build(); expose every dependency's lib dir to the
        # build environment or they cannot load libQt6Core.so.6.
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

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Application package: the delivered product is bin/kmousetool.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
