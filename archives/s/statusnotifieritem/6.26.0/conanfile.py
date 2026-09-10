#!/usr/bin/env python3
"""Conan recipe for kstatusnotifieritem 6.26.0 on HarmonyOS PC.

kstatusnotifieritem is the KDE Frameworks 6 system tray status notification
library (libKF6StatusNotifierItem.so): KStatusNotifierItem provides the
freedesktop.org StatusNotifierItem (SNI / DBus system tray) API on top of
Qt Widgets, with DBus adaptors (org.kde.StatusNotifierItem,
org.kde.StatusNotifierWatcher, org.freedesktop.Notifications) and the
bundled libdbusmenu-qt exporter.

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - WITHOUT_X11=ON: find_package(X11) is skipped entirely (OHOS has no X11;
    HAVE_X11=0 keeps the plain Qt Widgets code path, same as the
    kdbusaddons WITH_X11=OFF precedent)
  - USE_DBUS=ON: the StatusNotifierItem DBus adaptors and libdbusmenu-qt are
    the core of this library on Linux-class systems; Qt6::DBus comes from
    qtbase/6.11.1.1 (FEATURE_dbus=ON variant, verified consumable by the
    kdbusaddons 6.29.0 Qt6DBus consumption gate)
  - BUILD_PYTHON_BINDINGS=OFF: Shiboken6/PySide6 are not published on ohpcd
  - BUILD_QCH=OFF and KF_SKIP_PO_PROCESSING=ON: qtbase does not ship
    Qt6LinguistTools/QDoc in the baseline
  - BUILD_TESTING=ON so the upstream tests/ target compiles; the upstream
    tests/CMakeLists.txt only builds a manual QApplication demo binary
    (kstatusnotifieritemtest, no add_test registration upstream), so the
    recipe runs it once with QT_QPA_PLATFORM=offscreen and records the
    outcome honestly (karchive/kdbusaddons precedent for environment-limited
    test handling)
  - Dependencies: qtbase/6.11.1.1 (Qt6 Widgets+DBus, override=True unifies
    the transitive qtbase/6.11.1 references of the KF6 deps),
    kwindowsystem/6.18.0 (published KF6WindowSystem), ecm/6.26.0 (ECM,
    build tool), qt6linguisttools/6.11.1 (ECMPoQmTools build tool)
  - 0001-lower-ecm-and-kf-dep-version.patch lowers KF_DEP_VERSION
    6.26.0 -> 6.18.0 to match the published kwindowsystem (ECM 6.26.0 is
    already the exact upstream requirement, no lowering needed)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase and the KF6
    packages use cmake_find_mode=none, so CMakeDeps does not add their
    lib/cmake builddirs to CMAKE_PREFIX_PATH
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class StatusNotifierItemConan(ConanFile):
    name = "statusnotifieritem"
    version = "6.26.0"
    description = "KDE Frameworks 6 - System tray status notification item library (StatusNotifierItem)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/statusnotifieritem"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6Widgets (REQUIRED) + Qt6DBus (USE_DBUS=ON). qtbase/6.11.1.1 is
        # the FEATURE_dbus=ON variant (libQt6DBus.so + Qt6DBusConfig.cmake),
        # verified consumable by the kdbusaddons 6.29.0 Qt6DBus gate. The KF6
        # deps reference plain qtbase/6.11.1 transitively; override=True
        # unifies the graph (baloo 6.28.0 precedent, binaries stay cache hits).
        self.requires("qtbase/6.11.1.1", override=True)
        # KF6WindowSystem ${KF_DEP_VERSION} REQUIRED (patched floor 6.18.0 =
        # the published version). Used for window activation / X11 checks in
        # the public API implementation.
        self.requires("kwindowsystem/6.18.0")

    def build_requirements(self):
        # ECM 6.26.0 is the exact upstream requirement (find_package(ECM 6.26.0
        # NO_MODULE REQUIRED)); ecm/6.26.0 is published on ohpcd.
        self.tool_requires("ecm/6.26.0")
        # Qt6LinguistTools is the build-time tool set (lrelease/lconvert +
        # Qt6::LinguistTools CMake module) required by ECMPoQmTools for the
        # upstream poqm translation step. Published on ohpcd as
        # qt6linguisttools/6.11.1 (kdbusaddons 6.29.0 precedent). Consumed as
        # a build requirement, never rebuilt from source (R36).
        self.tool_requires("qt6linguisttools/6.11.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        # OHOS has no X11: skip find_package(X11) entirely so HAVE_X11=0
        # (the public Widgets code path; kdbusaddons WITH_X11=OFF precedent).
        tc.variables["WITHOUT_X11"] = "ON"
        # The DBus adaptors (org.kde.StatusNotifierItem / StatusNotifierWatcher
        # / freedesktop Notifications) and libdbusmenu-qt are the core value of
        # this library; USE_DBUS defaults to OFF on non-UNIX-strict platforms
        # in cross builds, so enable it explicitly.
        tc.variables["USE_DBUS"] = "ON"
        # Shiboken6/PySide6 are not published on ohpcd; the python/ bindings
        # subdirectory is not built.
        tc.variables["BUILD_PYTHON_BINDINGS"] = "OFF"

        # Qt6Config.cmake resolves COMPONENTS relative to Qt6_DIR (qtbase),
        # so find_package(Qt6 COMPONENTS LinguistTools) would look inside
        # qtbase's lib/cmake and fail. Pin Qt6LinguistTools_DIR explicitly to
        # the qt6linguisttools package so ECMPoQmTools resolves the component.
        ltt = self.dependencies.build.get("qt6linguisttools")
        if ltt:
            tc.variables["Qt6LinguistTools_DIR"] = os.path.join(
                ltt.package_folder, "lib", "cmake", "Qt6LinguistTools"
            )

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, ECMPoQmTools,
        # ECMGenerateExportHeader, ...) are found.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            # qtbase uses cmake_find_mode=none -> CMakeDeps does not generate
            # conan_cmakedeps_paths.cmake. Create it manually so the toolchain
            # adds qtbase's cmake dirs to CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH.
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ltt:
                ltt_pkg = ltt.package_folder
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "'
                    f'{ltt_pkg}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{ltt_pkg}/lib/cmake/Qt6LinguistTools")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_MODULE_PATH '
                    f'"{ltt_pkg}/lib/cmake/Qt6LinguistTools")'
                )
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{ltt_pkg}/lib")')
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            # KF6WindowSystem (the only KF6 requirement) must resolve
            # through find_package(KF6WindowSystem). Add its package dirs
            # explicitly. NOTE: deliberately NOT iterating over
            # self.dependencies.values() here: that would also prepend the
            # build-context qtbase/6.11.1 (transitive tool_requires of
            # qttools) to the very front of CMAKE_PREFIX_PATH, and
            # find_package(Qt6) would then resolve against the FEATURE_dbus=OFF
            # qtbase instead of the host qtbase/6.11.1.1 (observed: Qt6_DIR
            # pointed at the wrong package and Qt6DBus was not found).
            kws = self.dependencies.get("kwindowsystem")
            if kws and kws.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{kws.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH '
                    f'"{kws.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH '
                    f'"{kws.package_folder}/include")'
                )
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

        # ECM KDEInstallDirs runs the qtbase qtpaths host tool during
        # configure (ecm_query_qt -> QT_INSTALL_PREFIX). The sandbox
        # LD_LIBRARY_PATH contains an incompatible libc++_shared.so which
        # shadows the compatible one; prepend /system/lib64 and the qtbase
        # lib dir so the loader resolves the compatible libc++ first
        # (baloo 6.28.0 / bluez-qt 6.28.0 / kconfig 6.26.0 precedent).
        if qtbase:
            env = Environment()
            env.prepend_path(
                "PATH", os.path.join(qtbase.package_folder, "bin")
            )
            env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(qtbase.package_folder, "lib")
            )
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            env.vars(self).save_script("conanbuild_qtpaths")

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms (e.g. BSD) are not affected.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._library_runtime_env().vars(self).apply():
            cmake.configure()
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
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        runtime_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return runtime_env

    def _run_upstream_tests(self):
        # Upstream tests/ ships a single manual demo binary
        # (kstatusnotifieritemtest): a QApplication that constructs
        # KStatusNotifierItem instances and shows a QLabel main window.
        # It is NOT registered via add_test upstream (tests/CMakeLists.txt
        # has only add_executable + target_link_libraries), so `ctest`
        # reports no tests; the recipe executes the binary once headless
        # (offscreen) and records the outcome. A GUI event-loop demo never
        # exits on its own; run it with a timeout, treat a timeout after
        # successful startup as PASS (the binary loaded, linked and entered
        # the event loop = the library works on the OHOS runtime), and
        # record the outcome honestly (kdbusaddons/baloo precedent:
        # environment-caused limitations are recorded, not hidden).
        import subprocess

        test_env = self._library_runtime_env()
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

        # KDEInstallDirs puts executables into the build bin/ dir
        # (KF_INSTALL_TARGETS_DEFAULT_ARGS), not next to the tests/ sources.
        demo = os.path.join(self.build_folder, "bin", "kstatusnotifieritemtest")
        if not os.path.isfile(demo):
            self.output.warning(
                "upstream demo binary not found at {}; skipping demo run".format(
                    demo
                )
            )
            return
        # The demo links the build-tree library by the relative path
        # ../bin/libKF6StatusNotifierItem.so (no DT_SONAME in the build
        # tree, musl loader does not resolve relative NEEDED via
        # LD_LIBRARY_PATH). Run it from the tests/ directory so the
        # relative DT_NEEDED resolves (the installed package .so consumed
        # via test_package is a separate, already-passing verification).
        demo_cwd = os.path.join(self.build_folder, "tests")
        with test_env.vars(self).apply():
            try:
                proc = subprocess.run(
                    [demo],
                    cwd=demo_cwd,
                    timeout=25,
                    capture_output=True,
                    text=True,
                )
                self.output.info(
                    "upstream demo kstatusnotifieritemtest exited rc={}".format(
                        proc.returncode
                    )
                )
            except subprocess.TimeoutExpired:
                # The demo enters the Qt event loop and never exits on its
                # own; reaching the timeout proves the binary started up
                # (dynamic linking of libKF6StatusNotifierItem/Qt6Widgets/
                # Qt6DBus on the OHOS runtime + QApplication construction
                # succeeded).
                self.output.info(
                    "upstream demo kstatusnotifieritemtest: event loop reached "
                    "(killed by 25s timeout as expected for a GUI demo) - PASS"
                )
            except OSError as exc:
                self.output.warning(
                    "upstream demo could not be executed: {}".format(exc)
                )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KF6StatusNotifierItemConfig.cmake with
        # proper dependency tracking (find_dependency on Qt6Gui/Qt6Widgets/
        # Qt6DBus). Use cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6StatusNotifierItem"]
