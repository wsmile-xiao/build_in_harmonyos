#!/usr/bin/env python3
"""Conan recipe for kdecoration 6.7.2 on HarmonyOS PC.

kdecoration is the KDE Plasma window decoration plugin interface library
(libkdecorations3.so + libkdecorations3private.so, CMake package
KDecoration3). It provides the KDecoration3::KDecoration API used by
KWin window decorations (aurorae etc.).

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS
    is not in the KDE platform allowlist)
  - BUILD_TESTING=ON and ctest execution for the upstream autotests
    (decorationButtonTest, decorationTest, decorationShadowTest) with
    QT_QPA_PLATFORM=offscreen
  - Dependencies: qtbase/6.11.1 (Qt6Core/Qt6Gui/Qt6Test),
    ki18n/6.26.0 (KF6::I18n), ecm/6.26.0 (ECM, tool_requires)
  - ki18n path is added to CMAKE_PREFIX_PATH so find_package(KF6I18n)
    resolves the KF6I18nConfig.cmake installed by the conan package
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH
  - The po/ translation catalogs are skipped on OHOS (ki18n_install
    requires msgmerge from gettext tools; runtime i18n still resolves
    through KF6::I18n)
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KdecorationConan(ConanFile):
    name = "kdecoration"
    version = "6.7.2"
    description = "KDE Plasma - Plugin based library to create window decorations"
    license = "LGPL-2.1-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL"
    homepage = "https://invent.kde.org/plasma/kdecoration"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        # KDecoration3 links KF6::I18n for button tooltips/accessible names.
        self.requires("ki18n/6.26.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # kdecoration 6.7.2 uses C++20 (CMakeLists.txt sets
        # CMAKE_CXX_STANDARD 20). The conan toolchain variable_watch
        # mechanism overrides plain CMAKE_CXX_STANDARD, so force the
        # -std=c++20 flag via CMAKE_CXX_FLAGS like the kcoreaddons
        # 6.26.0 recipe does (proven approach for this toolchain).
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_CXX_FLAGS"] = "-std=c++20"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, etc.) are found.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qtbase = self.dependencies.get("qtbase")
        ki18n = self.dependencies.get("ki18n")
        if qtbase:
            qt_pkg = qtbase.package_folder
            # qtbase uses cmake_find_mode=none -> CMakeDeps does not generate
            # conan_cmakedeps_paths.cmake. Create it manually so the toolchain
            # adds qtbase's cmake dirs to CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH.
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ki18n:
                ki18n_pkg = ki18n.package_folder
                # KF6I18n installs lib/cmake/KF6I18n/KF6I18nConfig.cmake.
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ki18n_pkg}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH "{ki18n_pkg}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH "{ki18n_pkg}/include")'
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
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

        # CMake has no Platform/HarmonyOS module, so the generic platform
        # rules apply and CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG stays
        # undefined: no -Wl,-soname is passed to the linker and
        # libkdecorations3private.so ends up without a DT_SONAME entry.
        # libkdecorations3 links that in-tree sibling and the linker then
        # records a bin/- or lib/-relative NEEDED path, which the musl
        # loader cannot resolve after installation. Define the soname flag
        # explicitly (same value the Linux platform module uses) so both
        # libraries carry SONAMEs and the NEEDED entry stays a bare soname.
        toolchain_file = os.path.join(
            self.generators_folder, "conan_toolchain.cmake"
        )
        with open(toolchain_file, "a") as f:
            f.write(
                "\n"
                "# kdecoration: HarmonyOS platform module does not define a\n"
                "# soname flag; add the Linux-style flag so shared libraries\n"
                "# get a DT_SONAME entry.\n"
                'set(CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG "-Wl,-soname,")\n'
            )

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms are not affected.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
            # KDEInstallDirs (via ECMQueryQt) executes qtbase's qtpaths tool
            # during configure. The OHOS ELF binary needs libc++_shared.so
            # from the OHOS SDK; probe the SDK lib dirs and inject
            # LD_LIBRARY_PATH so the call succeeds (same class of fix as
            # ki18n 6.26.0's lld/libxml2 LD_LIBRARY_PATH workaround).
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
                                f"kdecoration: LD_LIBRARY_PATH += {sdk_lib}"
                            )
                            break
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
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
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            test_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error --timeout 90'.format(
                    self.build_folder
                )
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KDecoration3Config.cmake with proper
        # dependency tracking (find_dependency on Qt6Gui). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["kdecorations3", "kdecorations3private"]
