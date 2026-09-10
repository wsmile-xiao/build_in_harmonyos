#!/usr/bin/env python3
"""Conan test_package for baloo 6.28.0.

Verifies that KF6Baloo/KF6BalooEngine can be found via CMake and that the
core query/term/document APIs are callable (R34: real API usage).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class BalooTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # KF6BalooConfig.cmake does find_dependency(KF6CoreAddons) and
        # find_dependency(KF6FileMetaData), so the consumer graph needs both
        # packages for the dependency chain to resolve.
        self.requires("kcoreaddons/6.14.0")
        self.requires("kfilemetadata/6.14.0")
        self.requires("qtbase/6.11.1.1", override=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_CXX_FLAGS"] = "-std=c++20"
        tc.generate()

        qtbase = self.dependencies.get("qtbase")
        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if pkg:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{pkg.package_folder}/lib/cmake")'
            )
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")'
            )
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # E132: OHOS SDK lld depends on libxml2.so.16 shipped in the SDK's
        # llvm/lib directory. Prepend it so CMake's TryCompile can link
        # (kconfig 6.26.0 precedent).
        sdk_llvm_lib = (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"
            "/ohos/native/llvm/lib"
        )
        env = Environment()
        if os.path.isdir(sdk_llvm_lib):
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        env = Environment()
        env.append("LD_LIBRARY_PATH", [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ])
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        # E537 residual: some published KF6 dependencies (kfilemetadata/6.14.0)
        # record machine-private absolute Conan cache paths (an older
        # ~/.cache/conan2 layout) in their DT_NEEDED. The musl loader does not
        # fall back to LD_LIBRARY_PATH for absolute-path NEEDED entries, so
        # bridge the stale prefix with symlinks to the live cache. The bridge
        # is created only if the stale path is missing and the live package
        # exists (knewstuff 6.29.0 notes: the same absolute-path NEEDED class;
        # baloo's own libraries are patched to record basenames).
        self._bridge_stale_needed_prefixes()
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_baloo"),
                env="conanrun",
            )

    def _bridge_stale_needed_prefixes(self):
        stale_root = os.path.join(os.path.expanduser("~"),
                                  ".cache", "conan2", "p")
        live_root = os.path.join(os.path.expanduser("~"), ".conan2", "p")
        if not os.path.isdir(live_root):
            return
        for pkg_dir in os.listdir(live_root):
            live = os.path.join(live_root, pkg_dir)
            stale = os.path.join(stale_root, pkg_dir)
            if os.path.isdir(live) and not os.path.exists(stale):
                try:
                    os.makedirs(stale_root, exist_ok=True)
                    os.symlink(live, stale)
                except OSError:
                    pass
