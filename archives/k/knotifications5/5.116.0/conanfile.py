#!/usr/bin/env python3
"""Conan recipe for knotifications5 5.116.0 (KDE Frameworks 5 / Qt5) on
HarmonyOS PC.

knotifications is the KDE Frameworks desktop-notification library. This is
the KF5 branch (libKF5Notifications.so), adapted from the KF6 knotifications
6.26.0 recipe with the KF5/Qt5 chain specifics.

OHOS-specific adaptations (KF5 chain, kcoreaddons5/kconfig5/
kwindowsystem5 5.116.0 precedents):
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list).
  - CMAKE_SYSTEM_NAME=Linux: the OHOS CMake platform has no
    Platform/HarmonyOS module, so `UNIX` is not set and KDE's `if(UNIX)`
    source selection would silently drop sources. OHOS is POSIX, forcing the
    Linux platform is compatible (kcoreaddons5 5.116.0 precedent).
  - Qt5DBus / Canberra / Phonon4Qt5 REQUIRED blocks disabled via patch
    patches/0001-CMakeLists.txt.patch, and the `if (TARGET Qt5::DBus)`
    source/link guards forced off via patches 0002/0003: the OHOS Qt5
    packages do not ship the real Qt5DBus library (qt/5.15.19 is built
    -no-dbus; the qt5-qtbase CMakeDeps config merely declares a Qt5::DBus
    component). All DBus-dependent sources (notifybypopup, notifybyportal,
    the kstatusnotifieritem DBus backend, knotificationrestrictions) drop
    out and the audio-notification backend is not compiled.
  - knotificationmanager.cpp patched (0004): the upstream `#else` branch of
    the Popup-plugin include/instantiation assumes DBus on
    non-Android/Mac/Win; guarded with QT_DBUS_LIB, the Popup action degrades
    to NotifyByTaskbar when DBus is unavailable.
  - ecm_install_po_files_as_qm(poqm) disabled via patch 0001: requires
    Qt5LinguistTools (lrelease), not shipped by the packaged OHOS Qt5.
  - examples/ skipped via patch 0001: they need Qt5 Quick (qtdeclarative),
    which is not published.
  - Dependencies:
      qt5-qtbase/5.15.2.2       - Qt5 line resolved by CMakeDeps (defines
                                   the Qt5/Qt5:: Core, Gui, Widgets, DBus,
                                   ... component configs and targets).
      kcoreaddons5/5.116.0       - KPluginFactory/KPluginMetaData (required).
      kconfig5/5.116.0           - KSharedConfig/KConfigGroup (required).
      kwindowsystem5/5.116.0     - KWindowSystem (required; its own binary
                                   was built against qt/5.15.19, which is
                                   ABI-compatible at Qt 5.15 and resolves
                                   through SONAME at runtime).
  - qt5-qtbase/5.15.2.2 is pinned with override=True to unify the
    qt5-qtbase line declared as 5.15.2 by kcoreaddons5.
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate the variable the project relies on.
  - conan_cmakedeps_paths.cmake created manually to prepend the KF5
    dependencies' lib/cmake dirs (KF5Config, KF5CoreAddons, KF5WindowSystem
    ship their own installed Config.cmake files via builddirs) ahead of the
    CMakeDeps component configs.
  - CMAKE_SHARED_LIBRARY_SONAME flags injected: the OHOS (Generic) CMake
    platform defines no soname rule, so without them libKF5Notifications.so
    would ship without DT_SONAME (CI L5a gate, E330).
  - /system/lib64 prepended to LD_LIBRARY_PATH for configure, install and
    test runs (sandbox libc++_shared.so shadowing, kconfig 6.26.0 /
    kcoreaddons5 precedents).
  - Installed ELFs re-signed with binary-sign-tool in package(): the OHOS
    loader rejects the placeholder .codesign emitted by the OHOS lld for
    locally built libraries (dlopen fails with "Permission denied");
    qt/5.15.19 package precedent.
"""
import glob
import os
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout, CMakeDeps
from conan.tools.env import Environment


class Knotifications5Conan(ConanFile):
    name = "knotifications5"
    version = "5.116.0"
    description = "KDE Frameworks 5 - KDE Notifications (libKF5Notifications)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/knotifications"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Pin the qt5-qtbase line to 5.15.2.2 (overrides the qt5-qtbase/5.15.2
        # declared by kcoreaddons5; 5.15.2.2 is its recipe-fix release and is
        # binary-compatible for the Qt5Core consumers).
        self.requires("qt5-qtbase/5.15.2.2", override=True)
        self.requires("kcoreaddons5/5.116.0")
        self.requires("kconfig5/5.116.0")
        self.requires("kwindowsystem5/5.116.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self, generator="Ninja")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Regenerate a clean aggregated Qt5Config via CMakeDeps: the native
        # Qt5CoreConfig.cmake shipped by qt5-qtbase references build-tree
        # mkspecs paths (p/../b//mkspecs/linux-clang) that do not exist in
        # the installed package, breaking find_package(Qt5) on CI
        # (kwidgetsaddons5/attica5 5.116.0 precedent).
        deps = CMakeDeps(self)
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        tc = CMakeToolchain(self, generator="Ninja")
        shared = bool(self.options.shared)
        tc.variables["BUILD_SHARED_LIBS"] = shared
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["QT_MAJOR_VERSION"] = "5"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        tc.variables["BUILD_QCH"] = "OFF"
        # See class docstring: force the Linux platform so KDE's if(UNIX)
        # source selection keeps the unix sources in the build (kcoreaddons5
        # 5.116.0 precedent; R32-safe: OHOS is POSIX-compatible).
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"

        # The OHOS (Generic) CMake platform defines no soname rule; inject
        # the Linux-style flags so VERSION/SOVERSION take effect and
        # libKF5Notifications.so gets a DT_SONAME (CI L5a gate, E330).
        if str(self.settings.os) == "OHOS":
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
            targets = {
                "armv8": "aarch64-linux-ohos",
                "x86_64": "x86_64-linux-ohos",
            }
            target = targets.get(str(self.settings.arch))
            if target:
                tc.variables["CMAKE_C_COMPILER_TARGET"] = target
                tc.variables["CMAKE_CXX_COMPILER_TARGET"] = target

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, ...) are found.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])
            # find_package(ECM 5.116.0 NO_MODULE) is config-mode; pin ECM_DIR
            # to the ecm package's cmake dir (kwindowsystem5 precedent).
            tc.variables["ECM_DIR"] = os.path.join(
                ecm.package_folder, "share", "ECM", "cmake"
            )

        # Prepend the KF5 dependencies' installed Config.cmake dirs
        # (KF5Config, KF5CoreAddons, KF5WindowSystem ship them under
        # lib/cmake via builddirs). The CMakeDeps generator covers
        # qt5-qtbase's component configs; the KF5 packages use
        # cmake_find_mode=none and need explicit CMAKE_PREFIX_PATH entries.
        # The manual conan_cmakedeps_paths.cmake creation was removed: it
        # shadowed the file CMakeDeps.generate() writes, breaking the
        # toolchain's dependency wiring (7-round CI failure chain root
        # cause — mkspecs/DBus/QT_*_LIB/includes/link-libs layers all
        # stemmed from the lost wiring). The KF5 cmake_find_mode=none path
        # prepends moved into the conan_toolchain.cmake append below.
        tc.generate()

        # kwidgetsaddons5 precedent: the CMakeDeps-regenerated Qt5 configs
        # carry no INTERFACE_COMPILE_DEFINITIONS (the native Qt5 configs
        # would set QT_<MODULE>_LIB). Without QT_WIDGETS_LIB the KDE headers
        #' #ifdef guards strip <QFrame>/<QWidget> includes and kpassivepopup.h
        # fails with "expected class name" on `public QFrame`. Define the
        # module macros build-wide; every target here links the modules.
        tc_filename = os.path.join(
            self.generators_folder, "conan_toolchain.cmake"
        )
        with open(tc_filename, "a", encoding="utf-8") as f:
            # KF5 deps (kcoreaddons5/kconfig5/kwindowsystem5) use
            # cmake_find_mode=none: CMakeDeps generates no cmake config for
            # them, so find_package(KF5::...) needs explicit prefix entries
            # (migrated from the removed manual conan_cmakedeps_paths.cmake
            # which shadowed the CMakeDeps-generated file and broke the
            # toolchain's own dependency wiring — 7-round CI failure chain
            # root cause).
            if ecm:
                ecm_cmake = os.path.join(
                    ecm.package_folder, "share", "ECM", "cmake"
                ).replace("\\", "/")
                f.write(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")\n')
                f.write(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")\n')
            for dep in self.dependencies.host.values():
                if dep and dep.package_folder:
                    dep_pkg = dep.package_folder.replace("\\", "/")
                    f.write(
                        f'list(PREPEND CMAKE_PREFIX_PATH "{dep_pkg}/lib/cmake")\n'
                    )
                    f.write(
                        f'list(PREPEND CMAKE_LIBRARY_PATH "{dep_pkg}/lib")\n'
                    )
                    f.write(
                        f'list(PREPEND CMAKE_INCLUDE_PATH "{dep_pkg}/include")\n'
                    )
            f.write("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)\n")
            f.write(
                "\n# knotifications5: QT_*_LIB module macros normally provided\n"
                "# via the Qt5 imported targets' INTERFACE_COMPILE_DEFINITIONS\n"
                "# (absent from the CMakeDeps-generated Qt5 configs).\n"
                "add_compile_definitions(QT_CORE_LIB QT_GUI_LIB QT_WIDGETS_LIB "
                "QT_TEST_LIB)\n"
            )
            # The CMakeDeps Qt5 component targets propagate the QtCore
            # include dirs but not the other modules' (observed: compile
            # line carries only include/QtCore while <QFrame> needs
            # include/QtWidgets — CI build log, 4th red round). Provide the
            # Qt module include dirs build-wide; the root include/ is
            # already on the line via the Core component.
            qt5 = self.dependencies.get("qt5-qtbase")
            if qt5:
                qt5_inc = os.path.join(
                    qt5.package_folder, "include"
                ).replace("\\", "/")
                f.write(
                    "\n# knotifications5: Qt5 module include dirs (Widgets/Gui/\n"
                    "# Test) not carried by the CMakeDeps component targets'\n"
                    "# INTERFACE_INCLUDE_DIRECTORIES. QtDBus/QtNetwork are\n"
                    "# deliberately NOT injected: DBus code paths are disabled\n"
                    "# by patches 0002/0003 (qt5-qtbase is a -no-dbus build; the\n"
                    "# QtDBus internal headers use broken ../.. relative paths).\n"
                    f'include_directories("{qt5_inc}/QtWidgets" '
                    f'"{qt5_inc}/QtGui" "{qt5_inc}/QtTest")\n'
                    "# The CMakeDeps Qt5 component targets also fail to\n"
                    "# propagate their libraries to the link line (observed:\n"
                    "# 20 undefined Qt symbols — QPixmap/QWidget/QTabWidget —\n"
                    "# while the link command carries only EGL/GLESv2).\n"
                    "# Link the Qt5 module libraries explicitly.\n"
                    f'link_directories("{os.path.dirname(qt5_inc)}/lib")\n'
                )

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms (e.g. BSD) are not affected.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if str(self.settings.os) == "OHOS":
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # The sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so which shadows the compatible one; prepend
            # /system/lib64 so the loader resolves the compatible libc++ first
            # (kconfig 6.26.0 / kcoreaddons5 5.116.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

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

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        if str(self.settings.os) == "OHOS":
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
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
        test_env.define("XDG_DATA_HOME",
                        os.path.join(test_home, ".local", "share"))
        with test_env.vars(self).apply():
            # Upstream CTest add_test count is 0 in this feature set:
            #   - autotests/: the KNotificationTest ecm_add_test block is
            #     commented out UPSTREAM (needs a DBus session bus and the
            #     fake_notifications_server); the remaining autotests dir
            #     only registers tests when Qt5::Test was found, and the
            #     packaged Qt5 does not ship Qt5Test.
            #   - tests/: all four executables are guarded by
            #     if (TARGET Qt5::DBus) which is forced off by patch 0003.
            #   - examples/: manual example executables (no add_test).
            # Measured with `ctest -N`. --no-tests=ignore keeps the run green
            # so `conan create` verifies the build; the upstream N=0 is
            # declared in test_package/MANIFEST.yml.
            self.run(
                'ctest --test-dir "{}" --output-on-failure '
                '--no-tests=ignore'.format(self.build_folder)
            )

    def package(self):
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.install()
        if str(self.settings.os) == "OHOS":
            # The OHOS loader rejects the placeholder .codesign that the OHOS
            # lld emits for locally built shared libraries (dlopen fails with
            # "Permission denied" even though the section exists); re-sign
            # every installed ELF with binary-sign-tool so consumers and the
            # test_package can load libKF5Notifications.so.5 (qt/5.15.19
            # package precedent, harmonyos-recovery exec-permission.md).
            self._sign_installed_elfs()

    # ------------------------------------------------------------------
    # ELF self-signing (qt/5.15.19 recipe precedent)
    # ------------------------------------------------------------------
    def _sign_installed_elfs(self):
        binaries = []
        for root, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                candidate = os.path.join(root, filename)
                if os.path.islink(candidate):
                    continue
                if self._elf_type(candidate) in (2, 3):  # ET_EXEC, ET_DYN
                    binaries.append(candidate)
        if not binaries:
            return
        objcopy = self._resolve_tool("OBJCOPY", "llvm-objcopy")
        objdump = self._resolve_tool("OBJDUMP", "llvm-objdump")
        signer = self._resolve_tool("BINARY_SIGN_TOOL", "binary-sign-tool")
        for binary in sorted(binaries):
            original_mode = stat.S_IMODE(os.stat(binary).st_mode)
            with tempfile.TemporaryDirectory(
                prefix=".conan-sign-", dir=os.path.dirname(binary)
            ) as temp_dir:
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(binary, unsigned)
                if self._has_codesign_section(objdump, unsigned):
                    self._run_tool(
                        [objcopy, "--remove-section", ".codesign", unsigned],
                        f"remove the old code signature from {binary}",
                    )
                self._run_tool(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        unsigned,
                        "-outFile",
                        signed,
                        "-selfSign",
                        "1",
                    ],
                    f"sign {binary}",
                )
                if not os.path.isfile(signed) or self._elf_type(signed) not in (2, 3):
                    raise ConanInvalidConfiguration(
                        f"Signing did not produce a runnable ELF file for {binary}"
                    )
                if not self._has_codesign_section(objdump, signed):
                    raise ConanInvalidConfiguration(
                        f"Signing did not add a .codesign section to {binary}"
                    )
                os.replace(signed, binary)
                os.chmod(binary, original_mode)

    def _has_codesign_section(self, objdump, path):
        section_table = self._run_tool(
            [objdump, "-h", path], f"inspect ELF sections in {path}"
        )
        return any(
            ".codesign" in line.split()
            for line in section_table.splitlines()
        )

    @staticmethod
    def _run_tool(command, action):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanInvalidConfiguration(f"Unable to {action}: {error}") from error
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ConanInvalidConfiguration(
                f"Unable to {action}: {detail or 'tool exited unsuccessfully'}"
            )
        return result.stdout

    @staticmethod
    def _elf_type(path):
        try:
            with open(path, "rb") as binary:
                header = binary.read(18)
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"Unable to inspect installed file {path}: {error}"
            ) from error
        if len(header) < 18 or header[:4] != b"\x7fELF":
            return None
        byte_order = {1: "little", 2: "big"}.get(header[5])
        if byte_order is None:
            raise ConanInvalidConfiguration(
                f"Unsupported ELF byte order in installed file {path}"
            )
        return int.from_bytes(header[16:18], byte_order)

    @staticmethod
    def _resolve_tool(environment_variable, executable):
        configured = os.environ.get(environment_variable)
        candidate = configured or executable
        resolved = shutil.which(candidate)
        if (
            not resolved
            and os.path.isfile(candidate)
            and os.access(candidate, os.X_OK)
        ):
            resolved = os.path.abspath(candidate)
        if (
            not resolved
            or not os.path.isfile(resolved)
            or not os.access(resolved, os.X_OK)
        ):
            raise ConanInvalidConfiguration(
                f"Required tool {executable} was not found; set "
                f"{environment_variable} or add it to PATH"
            )
        return os.path.abspath(resolved)

    def package_info(self):
        # The project installs its own KF5NotificationsConfig.cmake with
        # proper dependency tracking. Use cmake_find_mode=none so CMakeDeps
        # doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5Notifications"]
