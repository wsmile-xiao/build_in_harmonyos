#!/usr/bin/env python3
"""Conan consumer test for libnm 1.58.0 (HarmonyOS PC)."""

import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibnmTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 把 glib 提升为「直接」依赖。原因：当 glib 仅作为 libnm 的传递依赖
        # （经 libnm 的 cpp_info.requires 引用其组件）时，conan 会把 glib 归入
        # "Skipped binaries"，其 cpp_info（含 include 目录）在生成 CMakeDeps 数据
        # 时被清空 ⇒ 消费者编译 <NetworkManager.h>（无条件 #include <gio/gio.h>）
        # 报 'gio/gio.h' file not found。提升为直接 require 后 glib 的 cpp_info
        # 恢复正常。这是仓库既有先例做法（见
        # archives/a/abiword-plugin-openwriter/3.0.8/test_package/conanfile.py）。
        self.requires("glib/2.88.3")

    def layout(self):
        cmake_layout(self)

    def _runtime_paths(self):
        paths = []
        seen = set()
        for requirement, dependency in self.dependencies.items():
            if requirement.build or requirement.test:
                continue
            if not dependency.package_folder:
                continue
            for libdir in dependency.cpp_info.libdirs:
                libdir = os.fspath(libdir)
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                libdir = os.path.abspath(libdir)
                if not os.path.isdir(libdir):
                    continue
                identity = os.path.normcase(libdir)
                if identity in seen:
                    continue
                seen.add(identity)
                paths.append(libdir)
        return paths

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"])

    def test(self):
        if not can_run(self):
            self.output.info("NOT_RUN LIBNM_CONSUMER=0/1 reason=cross_building")
            return

        dependency = self.dependencies[self.tested_reference_str]
        package_lib = os.path.abspath(
            os.path.join(dependency.package_folder, "lib")
        )
        if not os.path.isdir(package_lib):
            raise ConanInvalidConfiguration(
                f"libnm package library directory is missing: {package_lib}"
            )

        # E316 实体化闭环：运行时 SONAME 必须是规则文件
        soname_pattern = re.compile(r"^libnm[.]so[.][0-9]+$")
        sonames = [
            os.path.join(package_lib, name)
            for name in os.listdir(package_lib)
            if soname_pattern.fullmatch(name)
            and os.path.isfile(os.path.join(package_lib, name))
            and not os.path.islink(os.path.join(package_lib, name))
        ]
        if len(sonames) != 1:
            raise ConanInvalidConfiguration(
                f"expected one regular runtime SONAME libnm.so.<n>, "
                f"found {len(sonames)}"
            )
        alias = os.path.join(package_lib, "libnm.so")
        if os.path.islink(alias) or not os.path.isfile(alias):
            raise ConanInvalidConfiguration(
                f"link-time alias must be a regular file: {alias!r}"
            )
        self.output.info(f"LIBNM_RUNTIME_SONAME={sonames[0]}")

        runtime_paths = self._runtime_paths()
        if package_lib not in runtime_paths:
            runtime_paths.insert(0, package_lib)
        runtime_path = os.pathsep.join(runtime_paths)

        self.run(
            f"LD_LIBRARY_PATH={shlex.quote(runtime_path)} "
            f"LIBNM_TEST_SONAME={shlex.quote(sonames[0])} ./test_libnm",
            env="conanrun",
            scope="run",
        )
