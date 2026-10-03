#!/usr/bin/env python3
"""Conan test_package for kunifiedpush 26.04.0.

Verifies that the KUnifiedPush client library can be found via CMake and
that KUnifiedPush::Connector is constructible with a real D-Bus adaptor
registration plus a VAPID public-key round-trip (R34: real API usage).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KUnifiedPushTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("openssl/3.5.6.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        # kunifiedpush (cmake_find_mode=none) and qtbase-sql-dbus are found
        # through their installed CMake config files; expose every dependency
        # prefix manually (kcrash 6.26.0 test_package precedent).
        lines = [
            'set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)',
        ]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}")'
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
                    f'list(PREPEND CMAKE_MODULE_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
        lines.append(
            f'list(PREPEND CMAKE_PREFIX_PATH "${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        lines.append(
            f'list(PREPEND CMAKE_MODULE_PATH "${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # E132: the OHOS SDK lld depends on libxml2.so.16 shipped in the
        # SDK llvm/lib directory; prepend it so CMake TryCompile can link.
        env = Environment()
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
        env = Environment()
        env.append("LD_LIBRARY_PATH", [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ])
        for p in self.dependencies.values():
            if p.package_folder:
                env.append("LD_LIBRARY_PATH", os.path.join(p.package_folder, "bin"))
        # Connector registers its D-Bus adaptors on the session bus; the
        # offscreen plugin keeps Qt from touching a display.
        env.define("QT_QPA_PLATFORM", "offscreen")
        # Deterministic writable XDG/HOME for the ConnectorPrivate::loadState
        # QSettings state file.
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", test_home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        if self.settings.os == "OHOS":
            # The CI sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so shadowing the compatible one; prepend
            # /system/lib64 (kcrash 6.26.0 test_package precedent).
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            sdk_llvm_lib = (
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"
                "/ohos/native/llvm/lib"
            )
            if os.path.isdir(sdk_llvm_lib):
                env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kunifiedpush"),
                env="conanrun",
            )
