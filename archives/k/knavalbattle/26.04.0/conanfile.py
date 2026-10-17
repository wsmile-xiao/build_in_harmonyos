#!/usr/bin/env python3
"""Conan recipe for knavalbattle 26.04.0 on HarmonyOS PC (aarch64).

knavalbattle is the KDE Gear "Naval Battle" board game (Qt6 Widgets +
KF6 framework libraries + libkdegames KDEGames6 renderer).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass the KDE platform detection
    (OHOS is not in the KDE platform list)
  - KF_SKIP_PO_PROCESSING=ON: skip .po -> .qm translation catalog
    generation (no LinguistTools/gettext toolchain needed at build time)
  - DocBook handbook processing is patched out (patches/0001): the kdoctools
    meinproc6/DocBook XSL toolchain is not part of the OHOS baseline and the
    handbook is not needed by the game binary. The KF6 DocTools component is
    removed from find_package(KF6 COMPONENTS ...) and kdoctools is dropped
    from the graph: its published binary is built against karchive/6.19.0,
    which conflicts with libkdegames' karchive/6.18.0 override (the karchive
    override changes kdoctools' package_id, forcing a source rebuild that
    cannot complete in the sandbox).
  - Dependency versions: the KF6 frameworks that libkdegames/26.04.0
    pins to the 6.18.0 line (kcoreaddons/kconfig/ki18n/kcompletion/
    kwidgetsaddons/kxmlgui) are kept at 6.18.0 here to keep the graph
    single-version (Conan forbids two versions of one package). The
    components libkdegames does not pull (kcrash/kdbusaddons/
    ktextwidgets/kdnssd) use their published versions; the
    overrides below neutralize the lower 6.14.0 requires of
    ktextwidgets/6.14.0.
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated
    ECMConfig does not propagate the variable the project CMakeLists.txt
    relies on; conan_cmakedeps_paths.cmake written manually because the
    KF6/qtbase packages use cmake_find_mode=none, which prevents
    CMakeDeps from adding their lib/cmake dirs to CMAKE_PREFIX_PATH.
  - The packaged bin/knavalbattle is signed with the OHOS
    binary-sign-tool (ELF must be signed to be executable on device).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class KnavalbattleConan(ConanFile):
    name = "knavalbattle"
    version = "26.04.0"
    description = (
        "KDE Gear Naval Battle - the classic ship-sinking strategy board "
        "game for two players (local or over the network)"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://apps.kde.org/knavalbattle"
    url = "https://download.kde.org/stable/release-service/26.04.0/src/knavalbattle-26.04.0.tar.xz"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6: Widgets (QApplication/UI), Xml/Network (protocol) come from qtbase
        # (6.11.1, the version the libkdegames closure was built against).
        # qtbase-sql-dbus/6.11.1 supplies the Qt6DBus component that
        # kdbusaddons needs (kdbusaddons/6.29.0 requires qtbase/6.11.1.1 which
        # is the only qtbase variant that ships Qt6DBus, and it cannot coexist
        # with libkdegames' qtbase/6.11.1 — so kdbusaddons 6.14.0, built
        # against qtbase-sql-dbus, is used instead).
        self.requires("qtbase/6.11.1")
        self.requires("qtbase-sql-dbus/6.11.1")
        # KF6 components matched to libkdegames/26.04.0's 6.18.0 closure so the
        # graph stays single-version (Conan conflict rule). The overrides force
        # the 6.18.0 line: ktextwidgets/6.14.0 (the only published version)
        # requires 6.14.0-line kcompletion/kconfig/ki18n/kwidgetsaddons and
        # kdoctools/6.19.0 (dropped, see module docstring) would require
        # karchive/6.19.0. KF6 ABI is stable across these patch-level
        # releases, so the published binaries link cleanly.
        self.requires("karchive/6.18.0", override=True)
        self.requires("kcompletion/6.18.0", override=True)
        self.requires("kconfig/6.18.0", override=True)
        self.requires("kcoreaddons/6.18.0")
        self.requires("kcrash/6.18.0")
        self.requires("kdbusaddons/6.14.0")
        self.requires("kdnssd/6.29.0")
        self.requires("ki18n/6.18.0", override=True)
        self.requires("ktextwidgets/6.14.0")
        self.requires("kwidgetsaddons/6.18.0", override=True)
        self.requires("kxmlgui/6.18.0")
        # KDEGames renderer/highscore/theme framework (the only games-specific
        # runtime dependency, published to ohpcd).
        self.requires("libkdegames/26.04.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        self._write_cmake_paths(ecm)
        tc.generate()

    def _write_cmake_paths(self, ecm):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                self._append_dependency_paths(lines, dep.package_folder)
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            lines.extend(
                [
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_share}/cmake")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/find-modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/kde-modules")',
                ]
            )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    @staticmethod
    def _append_dependency_paths(lines, package_folder):
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}/lib/cmake")')
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}")')
        lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{package_folder}/lib")')
        lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{package_folder}/include")')

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.configure()
            cmake.build()

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
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
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
                self.run(
                    f"{self._quote(objcopy)} --remove-section .codesign {self._quote(path)}",
                    ignore_errors=True,
                )
                self.run(
                    f"{self._quote(signer)} sign -inFile {self._quote(path)} "
                    f"-outFile {self._quote(path)} -selfSign 1"
                )
                signed += 1
        self.output.info(f"Signed {signed} OHOS package ELF file(s)")

    def package(self):
        cmake = CMake(self)
        with self._runtime_env(include_build=True).vars(self).apply():
            cmake.install()
        self._sign_ohos_elf_tree(self.package_folder)

    def _runtime_env(self, include_build=False):
        env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "libexec"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins"))
        # The host shell LD_LIBRARY_PATH carries whitespace-padded entries
        # (".../chipset-pub-sdk:         /system/lib64") the OHOS loader cannot
        # resolve; provide clean system library dirs explicitly (alligator
        # 26.04.0 recipe precedent).
        for system_lib in ("/system/lib64", "/system/lib64/platformsdk", "/system/lib64/ndk"):
            env.append_path("LD_LIBRARY_PATH", system_lib)
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def package_info(self):
        # Application package: the binary is resolved through bindirs; no
        # library exports needed.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        self.runenv_info.prepend_path(
            "QT_PLUGIN_PATH", os.path.join(self.package_folder, "plugins")
        )
