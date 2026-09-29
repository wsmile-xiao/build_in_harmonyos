#!/usr/bin/env python3
"""Conan test_package for knotifyconfig 6.26.0.

Consumer-side verification (R34: real API usage) of the exported
KF6NotifyConfig CMake package:

  * find_package(KF6NotifyConfig) resolves through the project-installed
    KF6NotifyConfigConfig.cmake -- the recipe sets cmake_find_mode=none so
    CMakeDeps does not shadow it with a generated one.
  * test_knotifyconfig drives KNotifyConfigWidget through a full
    read -> modify -> save round trip against a notifyrc file it seeds
    itself, exercising the OHOS-patched QLineEdit sound field.
  * on OHOS, test_knotifyconfig_elf.py checks the installed shared object is
    an AArch64 ELF64 with its SONAME links and the .codesign section.

The build/run environment mirrors kitemviews 6.26.0 / kiconthemes 6.26.0
(merged in main): QT_QPA_PLATFORM=offscreen for the headless widgets, the
SDK llvm/lib on LD_LIBRARY_PATH so CMake try-compiles can link, and every
dependency's lib dir on LD_LIBRARY_PATH at run time.
"""
import os
import sys

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KnotifyconfigTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        qtbase = self.dependencies.get("qtbase")
        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
        ]
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
        # Expose every contributor's cmake dir so the find_dependency()
        # chain in KF6NotifyConfigConfig.cmake resolves.
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
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # E132: the OHOS SDK lld depends on libxml2.so.16 shipped in the
        # SDK's llvm/lib directory, which CI workers may not export via
        # LD_LIBRARY_PATH. Prepend it so CMake's TryCompile can link
        # (kitemviews 6.26.0 / kiconthemes 6.26.0 precedent). Must not
        # clobber the conanbuild env on other hosts.
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
        env.append(
            "LD_LIBRARY_PATH",
            [
                os.path.join(p.package_folder, "lib")
                for p in self.dependencies.values()
                if p.package_folder
            ],
        )
        env.append(
            "QT_PLUGIN_PATH",
            [
                os.path.join(p.package_folder, "plugins")
                for p in self.dependencies.values()
                if p.package_folder
            ],
        )
        # KNotifyConfigWidget instantiates QWidgets; run headless.
        env.define("QT_QPA_PLATFORM", "offscreen")

        # Hermetic XDG roots. KNotifyEventList::fill() opens
        # $XDG_CONFIG_HOME/<app>.notifyrc and additionally scans
        # $XDG_DATA_DIRS for knotifications6/<app>.notifyrc; pinning both
        # keeps the round trip independent of whatever the worker has in
        # ~/.config or /usr/share.
        home = os.path.join(self.build_folder, "ohos-xdg")
        for sub in ("config", "configdirs", "data", "datadirs"):
            os.makedirs(os.path.join(home, sub), exist_ok=True)
        env.define("HOME", home)
        env.define("XDG_CONFIG_HOME", os.path.join(home, "config"))
        env.define("XDG_CONFIG_DIRS", os.path.join(home, "configdirs"))
        env.define("XDG_DATA_HOME", os.path.join(home, "data"))
        env.define("XDG_DATA_DIRS", os.path.join(home, "datadirs"))

        executable = os.path.join(
            self.cpp.build.bindirs[0], "test_knotifyconfig"
        )

        with env.vars(self).apply():
            # OHOS-specific: the installed shared object must be an AArch64
            # ELF64 with its SONAME links and the .codesign section.
            if str(self.settings.os) in ("OHOS", "HarmonyOS"):
                package_folder = self.dependencies[
                    self.tested_reference_str
                ].package_folder
                script = os.path.join(
                    self.recipe_folder, "test_knotifyconfig_elf.py"
                )
                self.run(
                    f'"{sys.executable}" "{script}" "{package_folder}"',
                    env="conanrun",
                )

            cmake = CMake(self)
            cmake.test()
            self.run(executable, env="conanrun")
