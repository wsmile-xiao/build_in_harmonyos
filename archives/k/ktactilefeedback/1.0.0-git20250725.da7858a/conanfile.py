#!/usr/bin/env python3
"""Conan recipe for ktactilefeedback 1.0.0-git20250725.da7858a on HarmonyOS PC.

ktactilefeedback is the KDE Plasma tactile/haptic feedback library (QtFeedback
API: QFeedbackActuator/QFeedbackEffect plus a declarative QML import and
feedbackd/mmk/hfd backends). It is a C++/CMake project requiring Qt6
(Core/Qml/Multimedia) and Extra CMake Modules (ECM).

OHOS-specific adaptations (all proven in the kdecoration 6.7.2 recipe):
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS
    is not in the KDE platform allowlist)
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate the variable the project's
    CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH
  - Qt6Qml_DIR/Qt6Multimedia_DIR set as CACHE entries: Qt6Config.cmake
    resolves each component DIR relative to the Qt6Config location
    (qtbase's lib/cmake) and cannot find Qt6Qml/Qt6Multimedia living in
    the qtdeclarative/qtmultimedia conan packages otherwise
  - CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG defined explicitly: the
    HarmonyOS platform module in CMake does not define a soname flag, so
    shared libraries would be installed without a DT_SONAME entry and the
    linkers records bin/lib-relative NEEDED paths that the loader cannot
    resolve (observed: plugins NEEDED ../../../feedback/libKTactileFeedback.so)
  - autotests run with QT_QPA_PLATFORM=offscreen and dependency lib dirs /
    QML import path on the search paths
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KtactilefeedbackConan(ConanFile):
    name = "ktactilefeedback"
    version = "1.0.0-git20250725.da7858a"
    description = "KDE Plasma - Tactile feedback library (QtFeedback API + QML bindings)"
    license = "LGPL-2.1-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL"
    homepage = "https://invent.kde.org/jbbgameich/ktactilefeedback"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6 Core + Qml + Multimedia are all needed: QFeedbackEffect uses
        # Qt6Core; the declarative import links Qt6Qml; the mmk backend uses
        # Qt6Multimedia. qtdeclarative/qtmultimedia pin qtbase/6.11.1.
        self.requires("qtbase/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("qtmultimedia/6.11.1")
        # The hfd-service and feedbackd backend plugins link Qt6::DBus and
        # call the qt_add_dbus_interface(s) CMake macros. The published
        # qtbase/6.11.1 binary is a slim build without the DBus module, while
        # qtbase-sql-dbus/6.11.1 (same upstream Qt 6.11.1, +Sql/+DBus) carries
        # the Qt6DBus component. Require both: qtbase stays the umbrella
        # Qt6_DIR provider for Core/Qml, qtbase-sql-dbus provides Qt6DBus.
        self.requires("qtbase-sql-dbus/6.11.1", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
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
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, etc.) are found.
        ecm = self.dependencies.build.get("extra-cmake-modules")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qtbase = self.dependencies.get("qtbase")
        qtsqldbus = self.dependencies.get("qtbase-sql-dbus")
        qtdeclarative = self.dependencies.get("qtdeclarative")
        qtmultimedia = self.dependencies.get("qtmultimedia")
        if qtbase:
            qt_pkg = qtbase.package_folder
            # qtbase uses cmake_find_mode=none -> CMakeDeps does not generate
            # conan_cmakedeps_paths.cmake. Create it manually so the toolchain
            # adds qtbase's cmake dirs to CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH.
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if qtdeclarative:
                qtd_pkg = qtdeclarative.package_folder
                # Qt6Qml/Qt6QmlTools configs live in qtdeclarative's lib/cmake.
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qtd_pkg}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qtd_pkg}/lib")')
                lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qtd_pkg}/include")')
                # Qt6Config.cmake resolves each component's _DIR relative to
                # its own location (qtbase's lib/cmake) via find_package(... PATHS
                # ${_qt_cmake_dir}), so Qt6Qml living in a separate package is
                # invisible unless its _DIR cache entry is set explicitly.
                lines.append(
                    f'set(Qt6Qml_DIR "{qtd_pkg}/lib/cmake/Qt6Qml" '
                    f'CACHE PATH "Qt6Qml config dir" FORCE)'
                )
                lines.append(
                    f'set(Qt6QmlTools_DIR "{qtd_pkg}/lib/cmake/Qt6QmlTools" '
                    f'CACHE PATH "Qt6QmlTools config dir" FORCE)'
                )
            if qtmultimedia:
                qtm_pkg = qtmultimedia.package_folder
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qtm_pkg}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qtm_pkg}/lib")')
                lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qtm_pkg}/include")')
                lines.append(
                    f'set(Qt6Multimedia_DIR "{qtm_pkg}/lib/cmake/Qt6Multimedia" '
                    f'CACHE PATH "Qt6Multimedia config dir" FORCE)'
                )
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
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
            # Qt6DBus lives inside the qtbase-sql-dbus package; Qt6Config cannot
            # find it via its own component-resolution logic alone, so force the
            # cache entries (same reason as Qt6Qml/Qt6Multimedia above).
            if qtsqldbus:
                qsd_pkg = qtsqldbus.package_folder
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qsd_pkg}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qsd_pkg}/lib")')
                lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qsd_pkg}/include")')
                lines.append(
                    f'set(Qt6DBus_DIR "{qsd_pkg}/lib/cmake/Qt6DBus" '
                    f'CACHE PATH "Qt6DBus config dir" FORCE)'
                )
                lines.append(
                    f'set(Qt6DBusTools_DIR "{qsd_pkg}/lib/cmake/Qt6DBusTools" '
                    f'CACHE PATH "Qt6DBusTools config dir" FORCE)'
                )
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

        # CMake has no Platform/HarmonyOS module, so the generic platform
        # rules apply and CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG stays
        # undefined: no -Wl,-soname is passed to the linker and the plugins
        # end up without a DT_SONAME entry, recording relative NEEDED paths
        # (../../../feedback/libKTactileFeedback.so) that the loader cannot
        # resolve after installation. Define the soname flag explicitly
        # (same value the Linux platform module uses).
        toolchain_file = os.path.join(
            self.generators_folder, "conan_toolchain.cmake"
        )
        with open(toolchain_file, "a") as f:
            f.write(
                "\n"
                "# ktactilefeedback: HarmonyOS platform module does not define a\n"
                "# soname flag; add the Linux-style flag so shared libraries\n"
                "# get a DT_SONAME entry.\n"
                'set(CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG "-Wl,-soname,")\n'
            )

    def build(self):
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
            # KDEInstallDirs (via ECMQueryQt) executes qtbase's qtpaths tool
            # during configure. The OHOS ELF binary needs libc++_shared.so
            # from the OHOS SDK; probe the SDK lib dirs and inject
            # LD_LIBRARY_PATH so the call succeeds (same class of fix as
            # kdecoration 6.7.2).
            cc_cfg = self.conf.get("tools.build:compiler_executables", default={})
            cc = cc_cfg.get("c") if isinstance(cc_cfg, dict) else None
            if not cc:
                cc = os.environ.get("CC")
            if cc:
                cc_dir = os.path.dirname(
                    os.path.realpath(cc) if os.path.islink(cc) else cc
                )
                sdk_lib_candidates = [
                    os.path.join(
                        cc_dir, "..", "lib", "aarch64-linux-ohos",
                    ),
                    os.path.join(
                        cc_dir, "..", "ohos-sdk.org", "*",
                        "ohos", "native", "llvm", "lib", "aarch64-linux-ohos",
                    ),
                    os.path.join(cc_dir, "..", "lib"),
                ]
                for pattern in sdk_lib_candidates:
                    matches = glob.glob(pattern)
                    if matches:
                        sdk_lib = os.path.realpath(matches[0])
                        if os.path.isdir(sdk_lib):
                            ld_path = os.environ.get("LD_LIBRARY_PATH", "")
                            os.environ["LD_LIBRARY_PATH"] = (
                                f"{sdk_lib}:{ld_path}" if ld_path else sdk_lib
                            )
                            self.output.info(
                                f"ktactilefeedback: LD_LIBRARY_PATH += {sdk_lib}"
                            )
                            break
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        # R51: run the upstream autotests (4 tests registered via ECMAddTests).
        test_env = Environment()
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
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                test_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                test_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                test_env.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
        for rel in (
            "bin",
            "lib",
            os.path.join("src", "feedback"),
            os.path.join("src", "imports"),
            os.path.join("src", "plugins", "feedback", "mmk"),
            os.path.join("src", "plugins", "feedback", "hfd-service"),
            os.path.join("src", "plugins", "feedback", "feedbackd"),
        ):
            test_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        # The Qt6 QML import (qmldir/plugins.qmltypes) lives in the source
        # tree src/imports/feedback but declares module org.kde.tactilefeedback;
        # the QML engine resolves the module as <import-path>/org/kde/
        # tactilefeedback. The autotests run before package() assembles
        # lib/qml/org/kde/tactilefeedback, so stage the module files plus the
        # compiled plugin into a private import root and point
        # QML2_IMPORT_PATH/QML_IMPORT_PATH at it.
        import shutil
        qml_import_root = os.path.join(self.build_folder, "qml-imports")
        qml_module_dir = os.path.join(
            qml_import_root, "org", "kde", "tactilefeedback"
        )
        os.makedirs(qml_module_dir, exist_ok=True)
        src_import_dir = os.path.join(
            self.source_folder, "src", "imports", "feedback"
        )
        for fname in ("qmldir", "plugins.qmltypes"):
            src = os.path.join(src_import_dir, fname)
            if os.path.isfile(src):
                shutil.copy(src, os.path.join(qml_module_dir, fname))
        plugin_so = os.path.join(
            self.build_folder, "src", "imports", "libdeclarative_feedback.so"
        )
        if os.path.isfile(plugin_so):
            shutil.copy(
                plugin_so, os.path.join(qml_module_dir, "libdeclarative_feedback.so")
            )
        test_env.prepend_path("QML2_IMPORT_PATH", qml_import_root)
        test_env.prepend_path("QML_IMPORT_PATH", qml_import_root)
        # Also cover the package_folder for later-stage consumers and the
        # staging install tree if present.
        test_env.prepend_path(
            "QML2_IMPORT_PATH",
            os.path.join(self.package_folder, "lib", "qml"),
        )
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error --timeout 120'.format(
                    self.build_folder
                )
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KTactileFeedbackConfig.cmake with
        # proper dependency tracking. Use cmake_find_mode=none so CMakeDeps
        # doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KTactileFeedback"]
