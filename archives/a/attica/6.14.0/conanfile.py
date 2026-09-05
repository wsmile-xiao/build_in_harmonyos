#!/usr/bin/env python3
"""Conan recipe for attica 6.14.0 on HarmonyOS PC.

Attica is the KDE Frameworks 6 Open Collaboration Services client library.

OHOS-specific adaptations (based on the attica/6.18.0 baseline recipe):
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - BUILD_TESTING=ON and ctest execution for upstream autotests
  - Dependencies: qtbase/6.11.1 and ecm/6.26.0 (ECM; attica 6.14.0 requires
    find_package(ECM 6.14.0 NO_MODULE), which ecm/6.26.0 already satisfies,
    so no ECM version patch is needed - unlike attica 6.28.0)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its lib/cmake
    builddir to CMAKE_PREFIX_PATH
  - configure() wrapped with a runtime env that prepends the OHOS SDK llvm
    lib dir: KDEInstallDirs6/ECMQueryQt executes qtbase's qtpaths at
    configure time, and the OHOS-built qtpaths needs libc++_shared.so /
    libunwind.so which qtbase's conan package does not ship
  - CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG injected: HarmonyOS is not a
    versioned-SONAME CMake platform, without it libKF6Attica.so would
    carry no DT_SONAME (CI L5 soname gate)
  - providertest excluded from CTest: it needs live external OCS endpoints
    (autoconfig.kde.org / invalid-url.org) that can hang on the OHOS runner
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class AtticaConan(ConanFile):
    name = "attica"
    version = "6.14.0"
    description = "KDE Frameworks 6 - Open Collaboration Services client library"
    license = "LGPL-2.1-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL"
    homepage = "https://invent.kde.org/frameworks/attica"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["ATTICA_STATIC_BUILD"] = "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # HarmonyOS is not mapped to a versioned CMake platform, so
        # CMAKE_SHARED_LIBRARY_SONAME_<lang>_FLAG stays undefined and the
        # produced libKF6Attica.so would have no ELF DT_SONAME (the CI L5
        # soname gate fails).  Mirror the platform-validated attica5/5.116.0
        # and expat pattern: keep SONAME emission but skip versioned symlinks.
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

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

        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines = [
                f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")',
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")',
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")',
            ]
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')

            lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # configure() is wrapped with the runtime env: KDEInstallDirs6 runs
        # qtbase's qtpaths at configure time, and the OHOS-built qtpaths needs
        # libc++_shared.so / libunwind.so from the OHOS SDK llvm lib dir
        # (qtbase's conan package does not ship them) plus the qtbase lib dir.
        with self._library_runtime_env().vars(self).apply():
            cmake.configure()
        with self._library_runtime_env().vars(self).apply():
            cmake.build()
        self._run_upstream_tests()

    def _library_runtime_env(self):
        runtime_env = Environment()
        # OHOS SDK runtime libraries (libc++_shared.so, libunwind.so) needed
        # by OHOS-built host tools such as qtbase's qtpaths, which
        # KDEInstallDirs6/ECMQueryQt executes at configure time.
        for sdk_lib in self._ohos_sdk_lib_dirs():
            runtime_env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                runtime_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        return runtime_env

    @staticmethod
    def _ohos_sdk_lib_dirs():
        """Locate OHOS SDK llvm lib dirs that provide libc++_shared.so.

        Falls back to the known-good SDK layout on both the local runner and
        CI machines; only existing directories are returned.
        """
        candidates = [
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos",
        ]
        # Wildcard fallback covers other SDK versions installed side by side.
        candidates.extend(
            glob.glob(
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/aarch64-linux-ohos"
            )
        )
        dirs = []
        for cand in candidates:
            if os.path.isdir(cand) and cand not in dirs:
                dirs.append(cand)
        return dirs

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
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
        self._prepare_ctest_runtime_links()
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error -E "^providertest$"'.format(
                    self.build_folder
                )
            )

    def _prepare_ctest_runtime_links(self):
        compatibility_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, "bin")
        )
        os.makedirs(compatibility_bin, exist_ok=True)
        lib_sources = glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*"))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        for src in lib_sources:
            dst = os.path.join(compatibility_bin, os.path.basename(src))
            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    os.symlink(src, dst)
                except OSError:
                    shutil.copy2(src, dst)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6Attica"]
