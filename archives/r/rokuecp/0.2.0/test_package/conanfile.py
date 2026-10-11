#!/usr/bin/env python3
"""Conan consumer tests for rokuecp 0.2.0."""

import os
import glob
import platform
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class RokuecpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        library_paths = []
        for dependency in self.dependencies.values():
            if not dependency.package_folder:
                continue
            for libdir in dependency.cpp_info.libdirs:
                path = libdir if os.path.isabs(libdir) else os.path.join(
                    dependency.package_folder, libdir
                )
                if path not in library_paths:
                    library_paths.append(path)
        ld_library_path = os.pathsep.join(library_paths)
        if platform.machine().lower() in ("aarch64", "arm64"):
            command = 'LD_LIBRARY_PATH="{}" ctest --output-on-failure'.format(
                ld_library_path
            )
            self.run(command, cwd=self.build_folder, env="conanrun")
            return

        # The development runner is x86_64. Run the same dynamically linked
        # OHOS AArch64 consumers through QEMU and an AArch64 musl root supplied
        # with QEMU_LD_PREFIX; never turn a missing emulator into a successful
        # skip. Native HarmonyOS PC CI takes the branch above.
        qemu = shutil.which("qemu-aarch64")
        qemu_root = os.environ.get("QEMU_LD_PREFIX", "")
        interpreter = os.path.join(qemu_root, "lib", "ld-musl-aarch64.so.1")
        if not qemu or not qemu_root or not os.path.isfile(interpreter):
            raise RuntimeError(
                "qemu-aarch64 and QEMU_LD_PREFIX with an AArch64 musl loader "
                "are required for cross-run tests"
            )

        for name in ("test_rokuecp", "test_rokuecp_ohos"):
            matches = glob.glob(os.path.join(self.build_folder, "**", name), recursive=True)
            binary = next((path for path in matches if os.path.isfile(path)), None)
            if not binary:
                raise RuntimeError(f"built test executable not found: {name}")
            self.run(
                '"{}" -L "{}" -E LD_LIBRARY_PATH="{}" "{}"'.format(
                    qemu, qemu_root, ld_library_path, binary
                ),
                env="conanrun",
            )
