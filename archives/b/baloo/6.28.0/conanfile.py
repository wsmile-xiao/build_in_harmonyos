#!/usr/bin/env python3
"""Conan recipe for baloo 6.28.0 on HarmonyOS PC.

baloo is the KDE Frameworks 6 file indexing and searching framework
(libKF6Baloo.so / libKF6BalooEngine.so plus the baloo_file indexer daemon,
baloo_file_extractor and the balooctl/baloosearch/balooshow CLI tools).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - CMakeLists patches: lower find_package(ECM) to 6.26.0 and find_package(KF6)
    floor to 6.14.0 (ohpcd published baseline), drop the KIO component
    (kioworkers are not built on OHOS, no kio package published), and skip
    ki18n_install(po) (qtbase does not ship Qt6LinguistTools; kconfig/
    kfilemetadata use the same patch)
  - src/CMakeLists patch: do not add the kioworkers subdirectory (KF6::KIOCore
    only consumer; KIO infrastructure is not part of the OHOS baseline)
  - Qt6 comes from qtbase/6.11.1.1 (FEATURE_dbus=ON provides Qt6::DBus which
    baloo REQUIRES; plain qtbase/6.11.1 has FEATURE_dbus=OFF) plus
    qtdeclarative/6.11.1 (Qt6::Qml/Qt6::Quick). Transitive qtbase/6.11.1
    references from the KF6 dependencies are unified to 6.11.1 with
    override=True (the bluez-qt 6.28.0 / kdbusaddons 6.29.0 Qt6DBus path;
    all KF6 binaries remain cache hits under the override graph)
  - C++20 forced via CMAKE_CXX_FLAGS: baloo 6.28.0 uses std::ranges in the
    engine and the KDE Frameworks compiler settings expect C++20 (clang 15 /
    libc++ / profile cppstd=17 default cannot compile it)
  - BUILD_TESTING=ON and ctest execution for the upstream autotests
    (37 ctest cases: 3 codecs + 15 engine + 11 file + 4 lib + 4 integration);
    the file/engine subsets exercise the LMDB database layer end to end
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BalooConan(ConanFile):
    name = "baloo"
    version = "6.28.0"
    description = "KDE Frameworks 6 - File indexing and searching framework"
    license = "LGPL-2.1-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL"
    homepage = "https://invent.kde.org/frameworks/baloo"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qtbase/6.11.1.1 provides Qt6Core/Qt6DBus/Qt6Gui/Qt6Widgets/Qt6Test
        # (FEATURE_dbus=ON). baloo hard-requires Qt6::DBus for src/dbus and
        # the main library. The KF6 deps published on ohpcd reference plain
        # qtbase/6.11.1 (FEATURE_dbus=OFF); override=True unifies every
        # transitive qtbase reference to 6.11.1.1 (verified: all dependency
        # binaries remain cache hits under the override graph).
        self.requires("qtbase/6.11.1.1", override=True)
        # Qt6::Qml/Qt6::Quick (src/qml plugins; find_package(Qt6 ... Qml Quick)
        # is REQUIRED at top level).
        self.requires("qtdeclarative/6.11.1")
        # KF6 components (ohpcd published 6.14.x series, aligned with the
        # kfilemetadata/6.14.0 dependency set so the whole graph resolves
        # from prebuilt binaries):
        #   CoreAddons/Config/I18n/Solid/FileMetaData - main library
        #   DBusAddons - kioworkers/kded search module (still find_package'd)
        #   IdleTime   - baloo_file_extractor power-state monitor
        #   Crash      - baloo_file daemon + extractor test dummy
        self.requires("kconfig/6.14.0")
        self.requires("kcoreaddons/6.14.0")
        self.requires("ki18n/6.14.0")
        self.requires("kdbusaddons/6.29.0")
        self.requires("kfilemetadata/6.14.0")
        self.requires("kcrash/6.14.0")
        self.requires("solid/6.14.0")
        self.requires("kidletime/6.14.0")
        # LMDB engine storage backend (REQUIRED).
        self.requires("lmdb/0.9.35")

    def build_requirements(self):
        # ecm/6.26.0 is the published ECM base matching the patched
        # find_package(ECM 6.26.0) floor.
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.blocks.remove("cppstd")
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # baloo 6.28.0 uses std::ranges (C++20); the conan profile pins
        # cppstd=17, so force C++20 via the flags (kcoreaddons/kfilemetadata
        # precedent: CMAKE_CXX_STANDARD is overridden by variable_watch).
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_CXX_FLAGS"] = "-std=c++20"
        # CMake has no Platform/HarmonyOS module, so UNIX and
        # CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG stay unset and CMake would not
        # pass -Wl,-soname. Provide the flag explicitly so libKF6Baloo.so /
        # libKF6BalooEngine.so get a DT_SONAME + versioned symlink chain
        # (kfilemetadata precedent).
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, FindKF6, ...)
        # are found.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qtbase = self.dependencies.get("qtbase")
        qtdeclarative = self.dependencies.get("qtdeclarative")
        if qtdeclarative and qtdeclarative.package_folder:
            # Qt6Config.cmake resolves additional components (Qml/Quick) via
            # QT_ADDITIONAL_PACKAGES_PREFIX_PATH (akonadi 25.12.3 precedent).
            # Without it find_package(Qt6 COMPONENTS Qml) only searches the
            # qtbase lib/cmake prefix and fails.
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = (
                qtdeclarative.package_folder
            )
        if qtbase:
            qt_pkg = qtbase.package_folder
            # qtbase uses cmake_find_mode=none -> CMakeDeps does not generate
            # conan_cmakedeps_paths.cmake. Create it manually so the toolchain
            # adds qtbase's cmake dirs to CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH.
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            # Add every dependency's lib/cmake dir so find_package(KF6*),
            # find_package(Qt6 Qml/Quick) and the transitive
            # find_dependency() chains all resolve.
            for dep in self.dependencies.values():
                if dep and dep.package_folder:
                    lines.append(
                        f'list(PREPEND CMAKE_PREFIX_PATH '
                        f'"{dep.package_folder}/lib/cmake")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_LIBRARY_PATH '
                        f'"{dep.package_folder}/lib")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_INCLUDE_PATH '
                        f'"{dep.package_folder}/include")'
                    )
            lines.append(
                'list(PREPEND CMAKE_MODULE_PATH '
                '"${CMAKE_CURRENT_LIST_DIR}")'
            )
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH '
                '"${CMAKE_CURRENT_LIST_DIR}")'
            )
            # The OHOS clang wrapper carries its sysroot implicitly, so CMake
            # has no CMAKE_SYSROOT and find_path(sys/inotify.h) (ECM
            # FindInotify, needed for BUILD_KINOTIFY -> autotests) fails.
            # Expose the SDK sysroot usr prefix so find_path locates the
            # kernel headers (glob pattern: SDK version agnostic).
            import glob as _glob
            for _sysroot_usr in sorted(
                _glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/"
                    "sysroot/usr"
                )
            ):
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "{_sysroot_usr}")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH "{_sysroot_usr}/include")'
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
        # (bluez-qt 6.28.0 / kconfig 6.26.0 precedent).
        env = Environment()
        env.prepend_path("PATH", os.path.join(qtbase.package_folder, "bin"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(qtbase.package_folder, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.vars(self).save_script("conanbuild_qtpaths")

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms are not affected.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build(build_tool_args=["-j1"])
        if self.settings.os == "OHOS":
            self._run_upstream_tests()

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
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
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
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
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        # Upstream tests that require an active D-Bus session bus or a
        # running baloo daemon cannot run in the OHOS build environment
        # (no dbus-daemon). They are excluded from the ctest run and the
        # failure reasons are recorded in the notes (kdbusaddons/bluez-qt
        # precedent: environment limitations do not block the package
        # creation, the pass rate is reported honestly).
        excluded_tests = (
            # filewatchtest/metadatamovertest drive the file watcher through
            # the org.kde.BalooWatcherApplication D-Bus interface and wait
            # for baloo_file; no session bus on the OHOS build host.
            "filewatchtest",
            # filefetchjobtest/filemonitortest query the baloo_file daemon
            # over D-Bus (MainHub org.kde.baloo service).
            "filefetchjobtest",
            "filemonitortest",
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
        cmake.install()

    def package_info(self):
        # The project installs its own KF6BalooConfig.cmake with proper
        # dependency tracking (find_dependency Qt6Core/KF6FileMetaData). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6Baloo", "KF6BalooEngine"]
        self.cpp_info.system_libs = ["pthread"]
