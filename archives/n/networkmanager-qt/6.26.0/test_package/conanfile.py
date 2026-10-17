#!/usr/bin/env python3
"""Conan test_package for networkmanager-qt 6.26.0.

Verifies that the KF6NetworkManagerQt CMake package and library can be found
and that the public API (ConnectionSettings / WirelessSetting / SecretAgent
header) is usable from a downstream project (R34: real API usage).

The upstream KF6NetworkManagerQtConfig.cmake performs
find_dependency(Qt6 Core/DBus/Network) and pkg_search_module(libnm, gio-2.0),
so this test also has to provide the Qt6 prefix (qtbase-sql-dbus +
qtdeclarative) and the generated libnm.pc / gio-2.0.pc.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.gnu import PkgConfigDeps


class NetworkmanagerQtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Same Qt6 prefixes the library was built against.
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("libnm/1.58.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # libnm.pc / gio-2.0.pc for the pkg_search_module() calls inside
        # KF6NetworkManagerQtConfig.cmake.
        PkgConfigDeps(self).generate()
        # The public NetworkManagerQt headers include <libnm/NetworkManager.h>
        # while the generated libnm.pc only exposes include/libnm; add the parent
        # include dir so consumers compile (see the main recipe).
        libnm = self.dependencies.get("libnm")
        if libnm and libnm.package_folder:
            pc_path = os.path.join(self.generators_folder, "libnm.pc")
            if os.path.isfile(pc_path):
                parent_include = f"-I{libnm.package_folder}/include"
                with open(pc_path) as handle:
                    lines = handle.readlines()
                changed = False
                for index, line in enumerate(lines):
                    if line.startswith("Cflags:") and parent_include not in line:
                        lines[index] = line.rstrip("\n") + f" {parent_include}\n"
                        changed = True
                if changed:
                    with open(pc_path, "w") as handle:
                        handle.writelines(lines)

        tc = CMakeToolchain(self)
        tc.variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = True

        pkg_config = shutil.which("pkg-config") or "/data/service/hnp/bin/pkg-config"
        if os.path.isfile(pkg_config):
            tc.variables["PKG_CONFIG_EXECUTABLE"] = pkg_config

        qt_declarative = self.dependencies.get("qtdeclarative")
        if qt_declarative and qt_declarative.package_folder:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = qt_declarative.package_folder

        prefixes, libraries, includes, modules = [], [], [], []

        def add(collection, value):
            value = value.replace("\\", "/")
            if value not in collection:
                collection.append(value)

        def add_package_folder(folder):
            if not folder:
                return
            add(prefixes, os.path.join(folder, "lib", "cmake"))
            add(prefixes, folder)
            add(libraries, os.path.join(folder, "lib"))
            add(includes, os.path.join(folder, "include"))
            add(modules, os.path.join(folder, "lib", "cmake"))

        for dep_name in ("qtbase-sql-dbus", "qtdeclarative"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                add_package_folder(dep.package_folder)

        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            if dep.ref.name in ("qtbase", "qtbase-sql-dbus"):
                continue
            add_package_folder(dep.package_folder)

        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            f'set(CMAKE_MODULE_PATH "{";".join(modules)};${{CMAKE_MODULE_PATH}}")',
        ]
        with open(os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"), "w") as handle:
            handle.write("\n".join(lines) + "\n")

        tc.generate()

    def _runtime_env(self):
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
        for rel in ("bin", "lib"):
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(
                glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")
            ):
                env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return env

    def build(self):
        with self._runtime_env().vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        env = self._runtime_env()
        tmpdir = os.path.join(self.build_folder, "test-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define("TMPDIR", tmpdir)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_networkmanager_qt"),
                env="conanrun",
            )
