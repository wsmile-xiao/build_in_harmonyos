#!/usr/bin/env python3
"""Conan test_package for ksvg 6.26.0.

Verifies that the KF6Svg library can be found via CMake and that the
KSvg::Svg / KSvg::FrameSvg API surface is callable, including the QImage
software rendering path (svg->image()) which is the core deliverable of
this library (R34: real API usage).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KsvgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        # KF6SvgConfig.cmake does not find_dependency() KF6Config, but the
        # exported KF6::Svg interface links KF6::ConfigCore; kconfig must be
        # in the consumer graph for the imported target to resolve.
        self.requires("kconfig/6.18.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        qtbase = self.dependencies.get("qtbase")
        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        lines = [
            'set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)',
        ]
        if pkg:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{pkg.package_folder}/lib/cmake")'
            )
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{qt_pkg}/lib/cmake")'
            )
            lines.append(
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")'
            )
            lines.append(
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")'
            )
        # Make every other dependency's cmake dir discoverable (KF6Config
        # for the exported KF6::Svg interface, etc.).
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
            f'list(PREPEND CMAKE_PREFIX_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        lines.append(
            f'list(PREPEND CMAKE_MODULE_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # E132: OHOS SDK lld depends on libxml2.so.16 shipped in the SDK's
        # llvm/lib directory; CI workers may not export it via
        # LD_LIBRARY_PATH. Prepend it so CMake's TryCompile can link.
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
        lib_dirs = [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ]
        env.append("LD_LIBRARY_PATH", lib_dirs)
        # The published kconfig/6.18.0 records sibling libraries in
        # DT_NEEDED as relative paths ("../../bin/libKF6ConfigCore.so");
        # the OHOS loader resolves them against the executable directory,
        # so create <exe_dir>/../../bin/ compatibility links to every
        # runtime library (kpackage 6.26.0 precedent).
        self._prepare_compat_links()
        # KSvg::Svg renders through QImage (software path); the offscreen
        # QPA platform keeps the run headless-safe.
        env.define("QT_QPA_PLATFORM", "offscreen")
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_ksvg"),
                env="conanrun",
            )

    def _prepare_compat_links(self):
        compat_bin = os.path.normpath(
            os.path.join(self.cpp.build.bindirs[0], os.pardir, os.pardir, "bin")
        )
        os.makedirs(compat_bin, exist_ok=True)
        import glob
        for lib_dir in [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ]:
            for src in glob.glob(os.path.join(lib_dir, "lib*.so*")):
                dst = os.path.join(compat_bin, os.path.basename(src))
                if not os.path.exists(dst):
                    try:
                        os.symlink(src, dst)
                    except OSError:
                        import shutil
                        shutil.copy2(src, dst)
