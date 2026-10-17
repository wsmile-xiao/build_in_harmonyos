#!/usr/bin/env python3
"""Conan recipe for isoimagewriter 26.04.0 on HarmonyOS PC (aarch64).

isoimagewriter (KDE Gear 26.04.0) is the "ISO Image Writer" utility: a Qt 6
Widgets application that writes a downloaded ISO image to a USB flash disk and
verifies the written media.  It is an application package (bin/isoimagewriter
plus the desktop/appdata/icon files), not a library.

Upstream build surface (CMake + ECM + Qt6 + KF6):

  find_package(Qt6 ... Network Widgets DBus Test)
  find_package(KF6 ... I18n CoreAddons WidgetsAddons IconThemes Archive Crash
                      Solid)
  find_package(Gpgmepp / QGpgmeQt6 CONFIG)   # optional, non-REQUIRED

OHOS-specific adaptations:

  - CMAKE_SYSTEM_NAME is HarmonyOS with the OHOS Conan toolchain
    (Platform/OHOS.cmake is Linux-derived).  Upstream's platform dispatch in
    isoimagewriter/CMakeLists.txt only knows Windows/Linux/FreeBSD and would
    fall into its `else()` branch, dropping platform_lin.cpp,
    usbdevicemonitor_lin.cpp and externalprogressbar_lin.cpp and producing
    undefined references.  patches/0001 therefore accepts HarmonyOS in the
    Linux branches (sources, Solid/DBus links and the .desktop/appdata
    install rules).  No platform macro is introduced.
  - Gpgmepp/QGpgmeQt6 are optional upstream (`find_package(... CONFIG)` without
    REQUIRED).  The published gpgmepp 1.23.2 has the Qt6 binding disabled, so
    QGpgmeQt6 is not found and upstream compiles the non-GPG variant
    (`_USE_GPG` undefined).  ISO signature verification is therefore not
    available in this build; this is an upstream-supported configuration, not
    a stub, and the remaining verification path is unchanged.
  - qtbase-sql-dbus/6.11.1 is used instead of qtbase/6.11.1 because upstream
    requires Qt6::DBus (platform_lin.cpp enumerates drives over the
    org.freedesktop.UDisks2 system bus).  The plain qtbase variant is built
    with FEATURE_dbus=OFF.
  - The published Qt6/KF6 packages use cmake_find_mode=none, so CMakeDeps does
    not put their lib/cmake dirs on CMAKE_PREFIX_PATH; generate() writes
    conan_cmakedeps_paths.cmake manually (kcrash 6.26.0 / alligator 26.04.0
    precedent).
  - ECM_MODULE_PATH is set explicitly because the CMakeDeps-generated
    ECMConfig.cmake does not propagate it.
  - KF_IGNORE_PLATFORM_CHECK=TRUE: HarmonyOS is not in KDE's platform list.
  - KF_SKIP_PO_PROCESSING=ON: upstream calls ki18n_install(po) at top level;
    the translation step needs msgfmt, which is not part of the build image
    (accessibility 26.04.3 / akonadi 25.12.3 precedent).
  - The installed ELF is re-signed with the OHOS signing tool, because the
    RPATH rewrite invalidates the original code signature and an unsigned ELF
    cannot be executed by test_package.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class IsoimagewriterConan(ConanFile):
    name = "isoimagewriter"
    version = "26.04.0"
    description = ("KDE ISO Image Writer: write an ISO image to a USB flash "
                   "disk (Qt 6 Widgets / KF6 application)")
    license = "GPL-3.0-or-later"
    homepage = "https://invent.kde.org/utilities/isoimagewriter"
    url = "https://download.kde.org/stable/release-service/26.04.0/src/isoimagewriter-26.04.0.tar.xz"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    options = {}
    default_options = {}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 Core/Gui/Widgets/Network/DBus/Test come from the
        # qtbase-sql-dbus variant (FEATURE_dbus=ON, required by
        # platform_lin.cpp's UDisks2 enumeration).
        self.requires("qtbase-sql-dbus/6.11.1")
        # KF6 frameworks used by upstream's find_package(KF6 ...) call.
        self.requires("karchive/6.26.0")
        self.requires("kcoreaddons/6.26.0")
        self.requires("kcrash/6.26.0")
        self.requires("ki18n/6.26.0")
        self.requires("kiconthemes/6.26.0")
        self.requires("kwidgetsaddons/6.26.0")
        self.requires("solid/6.26.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # Upstream ships no test suite at all (no autotests/ directory, no
        # enable_testing()/add_test()), so BUILD_TESTING keeps its default;
        # the packaged executable is verified by test_package.
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        self._write_cmake_paths()
        tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        tc.generate()

    def _write_cmake_paths(self):
        """Make find_package(Qt6/KF6/ECM ...) resolve to the real config files.

        qtbase-sql-dbus and every KF6 package set cmake_find_mode=none, so
        CMakeDeps does not generate a conan_cmakedeps_paths.cmake and does not
        add their lib/cmake dirs to CMAKE_PREFIX_PATH.  Write the file by hand
        (kcrash 6.26.0 / alligator 26.04.0 precedent).
        """
        prefixes, libraries, includes, modules = [], [], [], []

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
                add_unique(modules, os.path.join(dep.package_folder, "lib", "cmake"))

        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            add_unique(prefixes, os.path.join(ecm_share, "cmake"))
            for rel in ("modules", "find-modules", "kde-modules"):
                add_unique(modules, os.path.join(ecm_share, rel))

        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            f'set(CMAKE_MODULE_PATH "{";".join(modules)};${{CMAKE_MODULE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as handle:
            handle.write("\n".join(lines) + "\n")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            self._cmake_step("configure", cmake.configure)
            self._cmake_step("build", cmake.build)

    def package(self):
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            self._cmake_step("install", cmake.install)
        self._sign_ohos_elf_tree(self.package_folder)

    def _cmake_step(self, label, runner):
        """Run one CMake step with its stdout/stderr bound to a log file.

        ``ConanFile.run()`` hands the recipe process' output streams to the
        child; on this platform clang then fails on every compilation unit
        without emitting a single diagnostic line and make only reports
        "Error 1", while the identical command succeeds from a shell.  Binding
        each step to its own log keeps the build reproducible and preserves the
        full log for diagnosis (libncurses 6.6_p20260516 precedent).
        """
        log_dir = os.path.join(self.build_folder, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"{label}.log")
        self.output.info(f"CMake step '{label}' log: {log_path}")
        with open(log_path, "w") as log:
            try:
                runner(stdout=log, stderr=log)
            except Exception as error:
                self.output.error(
                    f"CMake step '{label}' failed; tail of {log_path}:"
                )
                try:
                    with open(log_path, "r", errors="replace") as handle:
                        tail = handle.read().splitlines()[-80:]
                except OSError:
                    tail = ["<log unavailable>"]
                self.output.error("\n".join(tail))
                raise ConanException(
                    f"CMake step '{label}' failed, full log: {log_path}"
                ) from error

    def package_info(self):
        # Application package: consumers resolve bin/isoimagewriter through
        # bindirs, there is no library to export.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []

    # ── OHOS helpers ────────────────────────────────────────────────────
    def _runtime_env(self, include_build=False):
        """LD_LIBRARY_PATH/PATH for configure, build and install.

        KDE's KDEInstallDirs6 (ECM 6.26) runs the qtbase qtpaths host tool
        during configure.  The inherited shell LD_LIBRARY_PATH carries
        whitespace-padded entries the OHOS loader cannot resolve and an
        incompatible libc++_shared.so under
        /data/storage/el1/bundle/libs/arm64, so the dependency library dirs
        and /system/lib64 are prepended explicitly (kcrash 6.26.0 / kconfig
        6.26.0 precedent).
        """
        env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                # KF6 packages also install their shared libraries under bin/.
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "libexec"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins"))
        for system_lib in ("/system/lib64", "/system/lib64/platformsdk", "/system/lib64/ndk"):
            env.append_path("LD_LIBRARY_PATH", system_lib)
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _find_ohos_tool(self, name):
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                candidates.append(os.path.join(os.path.dirname(compiler), name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        return next((path for path in candidates if path and os.path.isfile(path)), "")

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    def _sign_ohos_elf_tree(self, root_folder):
        """Re-sign every ELF in the package: the RPATH rewrite invalidates the
        original OHOS signature and an unsigned ELF cannot be executed."""
        if str(self.settings.os) not in ("OHOS", "HarmonyOS") or not os.path.isdir(root_folder):
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException("Cannot locate OHOS ELF signing tools")
        signed = 0
        for root, _, files in os.walk(root_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                self.run(f"{self._quote(objcopy)} --remove-section .codesign {self._quote(path)}", ignore_errors=True)
                self.run(f"{self._quote(signer)} sign -inFile {self._quote(path)} -outFile {self._quote(path)} -selfSign 1")
                signed += 1
        self.output.info(f"Signed {signed} OHOS package ELF file(s)")
