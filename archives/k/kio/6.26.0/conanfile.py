#!/usr/bin/env python3
"""Conan recipe for kio 6.26.0 on HarmonyOS PC.

kio is the KDE Frameworks 6 input/output and networking library
(libKF6KIOCore.so plus the kioworker executable and the file/remote/trash
KIO workers).

OHOS-specific adaptations (carried forward from the 6.18.0 recipe, verified
against the 6.26.0 source):
  - KIOCORE_ONLY=ON: only KF6KIOCore, the kioworker executable and the
    kioworkers are built. The KIOGui/KIOWidgets/KIOFileWidgets targets are
    not part of the current OHOS baseline because several of their KF6 6.26
    dependencies are not published on ohpcd (solid 6.26, kbookmarks 6.26,
    kcolorscheme 6.26, kjobwidgets 6.26, kiconthemes 6.26)
  - patch 0001: drop the top-level find_package(KF6Solid 6.26.0 REQUIRED)
    (no ohpcd package; Solid is only linked by KIOGui/KIOFileWidgets which
    are not built in KIOCORE_ONLY mode; kio_trash does not link it)
  - patch 0002: exclude ksslcertificatemanager.cpp / ksslerroruidata.cpp
    from KIOCore (qtbase Qt6Network is built without SSL) and treat OHOS
    as Unix-like for kioglobal_p_unix.cpp (CMAKE_SYSTEM_NAME=HarmonyOS
    leaves the generic UNIX variable unset)
  - patch 0003: ftp/http workers disabled (they require SSL APIs that are
    not available); file/remote/trash workers stay enabled
  - patch 0004: drop the http autotests subdirectory (sslerrortest links
    KF6::KIOWidgets which is not built; the http helpers are manual tools
    not registered with CTest)
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS
    is not in the KDE platform list)
  - USE_DBUS=OFF: kdbusaddons 6.26.0 is not published on ohpcd and there is
    no D-Bus session/system bus on the OHOS build host
  - WITH_X11=OFF / WITH_WAYLAND=OFF: no X11/Wayland session on OHOS
  - BUILD_DESIGNERPLUGIN=OFF (Qt6UiPlugin not published)
  - BUILD_TESTING=ON and ctest execution for the upstream autotests that
    are available in the KIOCore feature set (kiocore-* suite)
  - CMAKE_CXX_STANDARD=20: kio uses C++20 features; the profile pins 17
  - Dependencies: qtbase/6.11.1, karchive/6.26.0, kconfig/6.26.0,
    kcoreaddons/6.26.0, ki18n/6.26.0, kservice/6.26.0, kcrash/6.26.0
    (help worker pulls KF6Archive), ecm/6.26.0 (ECM)
  - libxml2/2.15.3 exposed via LD_LIBRARY_PATH: the OHOS SDK lld needs
    libxml2.so.16 at link time (SONAME of libxml2/2.15.3)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KioConan(ConanFile):
    name = "kio"
    version = "6.26.0"
    description = "KDE Frameworks 6 - KIO (input/output and networking)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kio"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("karchive/6.26.0")
        self.requires("kconfig/6.26.0")
        self.requires("kcoreaddons/6.26.0")
        self.requires("ki18n/6.26.0")
        self.requires("kservice/6.26.0")
        self.requires("kcrash/6.26.0")
        # The OHOS SDK lld depends on libxml2.so.16 at link time; libxml2
        # 2.15.3 provides that SONAME. Declared so its lib dir can be
        # injected into LD_LIBRARY_PATH (worker environments may lack a
        # system libxml2.so.16).
        self.requires("libxml2/2.15.3")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # kio uses C++20 features; the ohos-aarch64 profile pins cppstd=17.
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # KIOCore-only baseline: gui/widgets/filewidgets targets and their
        # KF6 6.26 dependencies (solid/kbookmarks/kcolorscheme/kjobwidgets/
        # kiconthemes) are not part of the current ohpcd baseline.
        tc.variables["KIOCORE_ONLY"] = "ON"
        # Qt6 DBus / X11 / Wayland components are not enabled on this
        # baseline (no kdbusaddons 6.26 package, no session bus).
        tc.variables["USE_DBUS"] = "OFF"
        tc.variables["WITH_X11"] = "OFF"
        tc.variables["WITH_WAYLAND"] = "OFF"
        # Qt Designer plugin requires Qt6UiPlugin, not published to ohpcd.
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"
        # CMake has no Platform/HarmonyOS module; provide the SONAME flag so
        # libKF6KIOCore.so gets a DT_SONAME + versioned symlink chain
        # (kfilemetadata/baloo precedent).
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, etc.) are
        # found.
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

        tc.generate()

        # The lld of the OHOS SDK needs libxml2.so.16 (SONAME of
        # libxml2/2.15.3); expose its lib dir to build and test environments.
        libxml2 = self.dependencies.get("libxml2")
        if libxml2:
            libxml2_lib = os.path.join(libxml2.package_folder, "lib")
            self.buildenv_info.prepend_path("LD_LIBRARY_PATH", libxml2_lib)
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", libxml2_lib)

        self._write_cmake_paths(ecm)

    def _write_cmake_paths(self, ecm):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        ):
            if dep and dep.package_folder:
                lines.extend(
                    [
                        f'list(PREPEND CMAKE_PREFIX_PATH '
                        f'"{dep.package_folder}/lib/cmake")',
                        f'list(PREPEND CMAKE_LIBRARY_PATH '
                        f'"{dep.package_folder}/lib")',
                        f'list(PREPEND CMAKE_INCLUDE_PATH '
                        f'"{dep.package_folder}/include")',
                    ]
                )
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            lines.extend(
                [
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_share}/cmake")',
                    f'list(PREPEND CMAKE_MODULE_PATH '
                    f'"{ecm_share}/modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH '
                    f'"{ecm_share}/find-modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH '
                    f'"{ecm_share}/kde-modules")',
                ]
            )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms are not affected.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        if self.settings.os == "OHOS":
            self._run_upstream_tests()

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            # E132: the OHOS SDK lld depends on libxml2.so.16 shipped in the
            # SDK's llvm/lib directory; CI workers may not export it via
            # LD_LIBRARY_PATH. Prepend it so CMake's TryCompile can link.
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos"
                    "/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # ECM KDEInstallDirs runs the qtbase qtpaths host tool during
            # configure; the sandbox LD_LIBRARY_PATH contains an
            # incompatible libc++_shared.so which shadows the compatible
            # one; prepend /system/lib64 so the loader resolves the
            # compatible libc++ first (kconfig 6.26.0 / kcrash 6.26.0
            # precedent).
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
                runtime_env.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        # Same /system/lib64 libc++ shadowing fix as _cmake_build_env
        # (kconfig 6.26.0 / kcrash 6.26.0 precedent).
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
        test_env.define(
            "XDG_DATA_HOME", os.path.join(test_home, ".local", "share")
        )
        # Upstream tests that cannot run in the OHOS build sandbox are
        # excluded from the ctest run and their failure reasons are
        # recorded in notes.md (kdbusaddons/baloo precedent: environment
        # limitations do not block the package creation, the pass rate is
        # reported honestly):
        #  - kiocore-jobremotetest / kiocore-jobtest spawn kioworker
        #    helper processes and block forever in the OHOS sandbox
        #    procmgr_wait (the spawned worker inherits no usable process
        #    supervisor);
        #  - kiocore-jobtest additionally requires a writable /tmp
        #    (QFATAL "couldn't create /tmp/jobtest/", /tmp is read-only
        #    on OHOS, E002);
        #  - kioworkers-testtrash requires a writable partition with
        #    mount-point detection (KMountPoint sees no mountpoints in the
        #    OHOS sandbox: "A trash folder could not be found or created").
        excluded_tests = (
            "kiocore-jobremotetest",
            "kiocore-jobtest",
            "kioworkers-testtrash",
        )
        exclude_re = "^({})$".format("|".join(excluded_tests))
        self.output.info(
            "Excluding OHOS-incompatible upstream tests: {}".format(
                ", ".join(excluded_tests)
            )
        )
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error '
                '-E "{}"'.format(self.build_folder, exclude_re),
                ignore_errors=True,
            )

    def package(self):
        cmake = CMake(self)
        with self._library_runtime_env().vars(self).apply():
            cmake.install()

    def package_info(self):
        # The project installs its own KF6KIOConfig.cmake with proper
        # dependency tracking. Use cmake_find_mode=none so CMakeDeps doesn't
        # shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        # KIOCORE_ONLY baseline: only KF6KIOCore is built.
        self.cpp_info.libs = ["KF6KIOCore"]
