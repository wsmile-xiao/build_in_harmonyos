#!/usr/bin/env python3
"""Conan test_package for kiconthemes 6.26.0.

Verifies that the KF6IconThemes library can be found via CMake and that
the KIconLoader API is callable (R34: real API usage).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KiconthemesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("karchive/6.26.0")
        self.requires("ki18n/6.26.0")
        self.requires("kwidgetsaddons/6.26.0")
        self.requires("kcolorscheme/6.26.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        tc.generate()

        qtbase = self.dependencies.get("qtbase")
        pkg = self.dependencies.get(
            self.tested_reference_str.split("/")[0]
        )
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
        # Expose all KF6/Qt6 deps so find_dependency() chains resolve.
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
        env = Environment()
        # E132: OHOS SDK lld depends on libxml2.so.16 shipped in the SDK's
        # llvm/lib directory; workers may not export it via LD_LIBRARY_PATH.
        # Prepend it so CMake's TryCompile can link (kitemviews 6.26.0
        # precedent). Must not clobber conanbuild env on other hosts.
        sdk_llvm_lib = (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"
            "/ohos/native/llvm/lib"
        )
        if os.path.isdir(sdk_llvm_lib):
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        # On OHOS, standard DT_SONAME entries need a co-located runtime
        # library directory. Preserve the legacy test_package/bin layout too.
        runtime_dirs = {
            os.path.join(self.build_folder, "..", "..", "bin"),
            self.cpp.build.bindirs[0],
        }
        for runtime_dir in runtime_dirs:
            os.makedirs(runtime_dir, exist_ok=True)
        for dep in self.dependencies.values():
            libdir = os.path.join(dep.package_folder, "lib") if dep.package_folder else None
            if not libdir or not os.path.isdir(libdir):
                continue
            for name in os.listdir(libdir):
                if not (name.startswith("lib") and ".so" in name):
                    continue
                source = os.path.join(libdir, name)
                for runtime_dir in runtime_dirs:
                    link = os.path.join(runtime_dir, name)
                    if not os.path.lexists(link):
                        os.symlink(source, link)

        env = Environment()
        env.append("LD_LIBRARY_PATH", [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ])
        # KIconLoader touches the icon theme system; run headless.
        env.define("QT_QPA_PLATFORM", "offscreen")
        with env.vars(self).apply():
            executable = os.path.join(self.cpp.build.bindirs[0], "test_kiconthemes")
            self.output.info("OHOS test executable dynamic section:")
            self.run("llvm-readelf -d {}".format(executable), ignore_errors=True)
            self.run(executable, env="conanrun")
            cmake = CMake(self)
            cmake.test()
