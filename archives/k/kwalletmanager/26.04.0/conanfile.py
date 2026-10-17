#!/usr/bin/env python3
"""Conan recipe for kwalletmanager 26.04.0 — KDE Wallet Manager.

kwalletmanager (KDE Gear 26.04.0) is the password management tool for the
KDE Wallet system: a Qt6 Widgets QApplication (kwalletmanager5) that lists,
creates, opens and edits KWallet wallets through the org.kde.KWallet D-Bus
interface, plus an optional KCM configuration module + KAuth helper
(disabled here through ENABLE_KAUTH=OFF).

Upstream registers no test suite (no tests/, autotests/ or add_test() in
the tarball — grep evidence in test_package/MANIFEST.yml). Consumer-side
verification is provided by test_package, which executes the installed
kwalletmanager5 binary (--version, --help) in offscreen mode and parses the
installed desktop-file / appstream / D-Bus service metadata against the
upstream install contract.

OHOS adaptations (patches/0001-ohos-trim-kio-sni-kcmutils-kdoctools.patch):

* KIO trimmed: upstream uses KIO in five call sites, all operating on local
  wallet/XML files picked via QFileDialog or drag-and-drop (storedGet /
  storedPut / CommandLauncherJob). The kio conan package is published only
  on the 6.26/6.14 KF6 lines while kwallet — the heart of this application
  — is published only on the 6.18 line; mixing the lines changes every KF6
  package id and no prebuilt binaries match (kgoldrunner 26.04.0 precedent).
  All five call sites are replaced by direct QFile / QProcess equivalents.
* StatusNotifierItem trimmed: the system-tray icon is optional on this
  platform (kstatusnotifieritem published only on the 6.26 line); the tray
  code is guarded by an #ifdef and always runs windowed.
* KCMUtils + KAuth trimmed: the KCM module (src/konfigurator) and its KAuth
  helper are disabled through ENABLE_KAUTH=OFF (kcmutils published only on
  the 6.26 line).
* kdoctools trimmed: the handbook toolchain is not part of the OHOS package
  set (audiocd 26.04.3 / kgoldrunner 26.04.0 precedent); BUILD_DOC becomes
  effective only when KF6DocTools is found.

Dependency line: qtbase-sql-dbus/6.11.1 as the Qt6 anchor (the only
published Qt6 with the complete DBus module + qdbusxml2cpp, matching the
kwallet/6.18.0 binary closure; plain qtbase/6.11.1 keeps anchoring the
remaining KF6 6.18 binaries — both qtbase packages coexist in one graph
without touching any package id, kio-kwallet 6.28.0 precedent) + KF6 6.18
line (karchive/kconfig/kconfigwidgets/kcoreaddons/kcrash/kdbusaddons/
ki18n/kservice/kwallet/kwindowsystem/kxmlgui), ecm/6.26.0 as the build
tool.
"""

import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class KwalletmanagerConan(ConanFile):
    name = "kwalletmanager"
    version = "26.04.0"
    description = ("KDE Wallet Manager - password management tool for the "
                   "KDE Wallet system (KDE Gear 26.04.0, Qt6 Widgets)")
    license = "GPL-2.0-or-later AND GFDL-1.2-only"
    homepage = "https://invent.kde.org/utilities/kwalletmanager"
    url = "https://download.kde.org/stable/release-service/26.04.0/src/kwalletmanager-26.04.0.tar.xz"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 anchor: qtbase-sql-dbus/6.11.1 is the only published Qt6 with
        # the complete DBus module + qdbusxml2cpp (plain qtbase/6.11.1 is
        # built with FEATURE_dbus=OFF and this application requires
        # Qt6::DBus). It matches the kwallet/6.18.0 binary closure; the
        # remaining KF6 6.18 binaries keep their natural qtbase/6.11.1
        # anchor, so both qtbase packages coexist in one graph without
        # touching any package id (kio-kwallet 6.28.0 precedent).
        self.requires("qtbase-sql-dbus/6.11.1")
        # KF6 6.18 line — must match the kwallet/6.18.0 binary closure
        # exactly (any version bump changes every downstream package id and
        # no prebuilt binaries remain).
        # karchive: force the 6.18.0 line for the whole graph. The newest
        # kiconthemes/6.18.0 recipe revision requires karchive/6.19.0, which
        # conflicts with every other 6.18 package's prebuilt binaries (they
        # all anchor karchive/6.18.Z). Same override as libkdegames/kgoldrunner.
        self.requires("karchive/6.18.0", override=True)
        # kitemviews + kcodecs: linked directly by src/manager
        # (KTreeWidgetSearchLine / KCodecs); upstream relied on KIO's
        # transitive find_dependency, which the KIO trim removes.
        self.requires("kcodecs/6.18.0")
        self.requires("kitemviews/6.18.0")
        self.requires("kconfig/6.18.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("kcrash/6.18.0")
        self.requires("kdbusaddons/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kservice/6.18.0")
        self.requires("kwallet/6.18.0")
        self.requires("kwindowsystem/6.18.0")
        self.requires("kxmlgui/6.18.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"kwalletmanager is adapted for Linux and OHOS, not "
                f"{self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # Skip translation catalog generation (audiocd 26.04.3 precedent:
        # the CI worker msgfmt fails to load its own libintl).
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # The KCM module + KAuth helper (src/konfigurator) are trimmed:
        # kcmutils is published only on the 6.26 KF6 line.
        tc.variables["ENABLE_KAUTH"] = "OFF"
        # The KF6DocTools component is trimmed; never let find_package
        # look for it (it would fail hard on the OHOS package set).
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools"] = "TRUE"
        # KDEInstallDirs single-prefix layout on conan (libkdegames
        # precedent).
        tc.variables["KDE_INSTALL_LIBDIR"] = "lib"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        # ECM's own ECMConfig.cmake sets ECM_MODULE_PATH but the
        # CMakeDeps-generated one does not (audiocd precedent).
        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )
        if str(self.settings.os) == "OHOS":
            # OHOS loader workaround (audiocd precedent): pin page size.
            tc.variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
        tc.generate()
        self._write_cmake_paths()

    def _write_cmake_paths(self):
        """qtbase and the KF6 packages use cmake_find_mode=none: CMakeDeps
        does not add their lib/cmake dirs to CMAKE_PREFIX_PATH, so wire
        them up manually (audiocd 26.04.3 / libkgapi 26.04.0 precedent)."""
        prefixes = []
        libraries = []
        includes = []
        modules = []

        def add_unique(collection, value):
            normalized = value.replace("\\", "/")
            if normalized not in collection:
                collection.append(normalized)

        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                add_unique(prefixes, os.path.join(dep.package_folder, "lib", "cmake"))
                add_unique(prefixes, dep.package_folder)
                add_unique(libraries, os.path.join(dep.package_folder, "lib"))
                add_unique(includes, os.path.join(dep.package_folder, "include"))
                add_unique(modules, os.path.join(dep.package_folder, "bin"))

        # qtbase-sql-dbus must come first in CMAKE_PREFIX_PATH so its
        # Qt6Config.cmake (with the DBus module + qdbusxml2cpp) wins over
        # the plain qtbase/6.11.1 one anchoring the KF6 6.18 binaries.
        qt_sql_dbus = self.dependencies.get("qtbase-sql-dbus")
        if qt_sql_dbus and qt_sql_dbus.package_folder:
            add_unique(prefixes, qt_sql_dbus.package_folder)
            add_unique(
                modules,
                os.path.join(
                    qt_sql_dbus.package_folder, "lib", "cmake", "Qt6", "platforms"
                ),
            )

        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            add_unique(prefixes, ecm_cmake)
            for rel in ("modules", "find-modules", "kde-modules"):
                add_unique(modules, os.path.join(ecm.package_folder, "share", "ECM", rel))

        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            f'set(CMAKE_PROGRAM_PATH "{";".join(modules)};${{CMAKE_PROGRAM_PATH}}")',
        ]
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _cmake_build_env(self):
        build_env = Environment()
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                build_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
        if str(self.settings.os) == "OHOS":
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # Sandbox LD_LIBRARY_PATH carries an incompatible libc++_shared.so
            # which shadows the compatible one; prepend /system/lib64 so the
            # loader resolves the compatible libc++ first (kcalendarcore
            # 6.26.0 / libkgapi 26.04.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def package(self):
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.install()
        copy(self, "LICENSES",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.build_modules["cmake_find_package"].append(
            os.path.join("lib", "cmake")
        )
        # Runtime helpers for consumers (test_package): the application
        # data and the KWallet D-Bus interface xml live under share/.
        self.runenv_info.prepend_path(
            "XDG_DATA_DIRS", os.path.join(self.package_folder, "share")
        )
        # Surface every dependency lib dir (including transitive
        # non-cmake-visible ones: gettext's libintl.so.8 behind ki18n,
        # libxkbcommon/expat behind qtbase, qtsvg behind kiconthemes) on
        # the run environment so consumer tests resolve every ELF
        # (kgoldrunner openal-soft precedent, generalized).
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib):
                    self.runenv_info.prepend_path("LD_LIBRARY_PATH", lib)
