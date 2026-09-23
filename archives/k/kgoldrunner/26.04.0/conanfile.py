#!/usr/bin/env python3
"""Conan recipe for kgoldrunner 26.04.0 — KDE Lode Runner style game.

kgoldrunner (KDE Gear 26.04.0) is the classic "collect the gold, avoid the
enemies" puzzle-action game built on Qt6 Widgets and the KDE Games
framework.  Upstream is a QApplication with a KgDifficulty/KGameStandardAction
driven main window; all game logic lives in the single kgoldrunner target.

Upstream registers no test suite (no tests/, autotests/ or add_test() in
the tarball — grep verified).  Consumer-side verification is provided by
test_package, which exercises the game-data level parser (KGrGameIO,
the file format core shared by the game and its level editor) against the
installed gamedata files in offscreen mode.

OHOS adaptations (patches/0001-ohos-trim-kio-kdoctools.patch):

* KIO trimmed: upstream uses KIO exactly once (KIO::mkpath to create the
  user levels directory).  The kio conan package is published on a 6.26
  KF6 line while libkdegames (required) is on the 6.18 line — mixing the
  two changes every KF6 package id and no prebuilt binaries match.  The
  single call is replaced by the equivalent QDir().mkpath() (creates the
  directory plus missing parents, returns true when already present).
* kdoctools trimmed: the handbook doc toolchain is not part of the OHOS
  package set (audiocd 26.04.3 precedent); doc/ and kdoctools_install(po)
  are removed from the build.

Dependency line: qtbase/6.11.1 + KF6 6.18 line pinned to match the
libkdegames/26.04.0 binary closure (kconfig/kconfigwidgets/kcoreaddons/
kcrash/kdbusaddons/ki18n/kwidgetsaddons/kxmlgui/kiconthemes), ecm 6.26.0
as the build tool (version-matched ECM modules are compatible with the
6.18 KF6 line, kio 6.26.0 recipe precedent).

Runtime environment: the game is a QApplication; on the OHOS worker it
runs with QT_QPA_PLATFORM=offscreen (kirigami-addons 1.13.0 / audiocd
26.04.3 test precedent).  The consumer test in test_package instantiates
the level parser offscreen only — no window is shown.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class KgoldrunnerConan(ConanFile):
    name = "kgoldrunner"
    version = "26.04.0"
    description = ("KDE Goldrunner game - collect gold, avoid enemies, dig "
                   "through bricks (KDE Games, Qt6 Widgets)")
    license = "GPL-2.0-or-later AND GFDL-1.2-or-later"
    homepage = "https://invent.kde.org/games/kgoldrunner"
    url = "https://download.kde.org/stable/release-service/26.04.0/src/kgoldrunner-26.04.0.tar.xz"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # KF6 6.18 line — must match the libkdegames/26.04.0 binary closure
        # exactly (any version bump changes every downstream package id and
        # no prebuilt binaries remain).
        self.requires("qtbase/6.11.1")
        self.requires("kconfig/6.18.0", options={"shared": True})
        self.requires("kconfigwidgets/6.18.0", options={"shared": True})
        self.requires("kcoreaddons/6.18.0", options={"shared": True})
        self.requires("kcrash/6.18.0", options={"shared": True})
        self.requires("kdbusaddons/6.18.0", options={"shared": True})
        self.requires("ki18n/6.18.0", options={"shared": True})
        self.requires("kwidgetsaddons/6.18.0", options={"shared": True})
        self.requires("kcodecs/6.18.0", options={"shared": True})
        self.requires("kxmlgui/6.18.0", options={"shared": True})
        self.requires("kiconthemes/6.18.0", options={"shared": True})
        self.requires("libkdegames/26.04.0")
        # karchive: force the 6.18.0 line for the whole graph. The newest
        # kiconthemes/6.18.0 recipe revision requires karchive/6.19.0, which
        # conflicts with every other 6.18 package's prebuilt binaries (they
        # all anchor karchive/6.18.Z). Same override as libkdegames itself.
        self.requires("karchive/6.18.0", override=True, options={"shared": True})

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"kgoldrunner is adapted for Linux and OHOS, not "
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
        # The KF6DocTools component is trimmed; never let find_package
        # look for it (it would fail hard on the OHOS package set).
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools"] = "TRUE"
        # KDEInstallDirs single-prefix layout on conan (libkdegames precedent)
        tc.variables["KDE_INSTALL_LIBDIR"] = "lib"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        # ECM's own ECMConfig.cmake sets ECM_MODULE_PATH but the
        # CMakeDeps-generated one does not (audiocd precedent).
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
        if self.settings.os == "OHOS":
            # OHOS loader workaround (audiocd precedent): pin page size.
            tc.variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
        tc.generate()

        # qtbase and the KF6 packages use cmake_find_mode=none, so
        # CMakeDeps does not generate conan_cmakedeps_paths.cmake. Create it
        # manually (audiocd / libkcddb precedent).
        lines = []
        # include every package whose cmake config may be reached through
        # find_dependency chains (KF6 configs find_dependency each other);
        # host dependencies + build tools (ecm) both contribute prefixes.
        all_pkgs = {}
        for dep in self.dependencies.values():
            if dep.package_folder:
                all_pkgs[dep.ref.name] = dep.package_folder
        for dep in self.dependencies.host.values():
            if dep.package_folder:
                all_pkgs[dep.ref.name] = dep.package_folder
        for dep in self.dependencies.build.values():
            if dep.package_folder:
                all_pkgs[dep.ref.name] = dep.package_folder
        for dep_name in sorted(all_pkgs):
            pkg = all_pkgs[dep_name]
            if True:
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}/lib/cmake")')
                for libdir in ("lib", "lib64"):
                    lines.append(
                        f'list(PREPEND CMAKE_LIBRARY_PATH "{pkg}/{libdir}")'
                    )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH "{pkg}/include")'
                )
                bindir = os.path.join(pkg, "bin")
                if os.path.isdir(bindir):
                    lines.append(f'list(PREPEND CMAKE_PROGRAM_PATH "{bindir}")')
        if ecm:
            ecm_pkg = ecm.package_folder
            ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PROGRAM_PATH "{ecm_pkg}/bin")')
        # KDEGames6 exports its own cmake config under lib/cmake/KDEGames6
        kdegames = self.dependencies.get("libkdegames")
        if kdegames and kdegames.package_folder:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{kdegames.package_folder}/lib/cmake/KDEGames6")'
            )
        lines.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append(
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            lines.append(
                f'set(CONAN_RUNTIME_LIB_DIRS "{qtbase.package_folder}/lib")'
            )
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
        # Host tools (kconfig_compiler / moc / uic / rcc) are OHOS binaries
        # needing libc++_shared from /system/lib64 plus the dependency lib
        # dirs on LD_LIBRARY_PATH (audiocd 26.04.3 precedent).
        build_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if self.settings.os == "OHOS":
            import glob as _glob
            for llvm_lib in sorted(
                _glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
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
        # Runtime helpers for consumers (test_package) — the game data is
        # installed under share/kgoldrunner.
        self.runenv_info.prepend_path(
            "XDG_DATA_DIRS", os.path.join(self.package_folder, "share")
        )
        # libKDEGames6.so NEEDs libopenal.so.1 (openal-soft is a transitive
        # requirement of libkdegames); surface its lib dir (and libsndfile's)
        # on the run environment so consumer tests can resolve every ELF.
        for dep_name in ("openal-soft", "libsndfile"):
            try:
                dep = self.dependencies.get(dep_name)
            except Exception:
                dep = None
            if dep and dep.package_folder:
                lib = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib):
                    self.runenv_info.prepend_path("LD_LIBRARY_PATH", lib)
