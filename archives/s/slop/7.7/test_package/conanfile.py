#!/usr/bin/env python3
"""Consumer tests for slop 7.7."""

import os
import platform
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class SlopTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        package = self.dependencies["slop"]
        binary = os.path.join(package.package_folder, "bin", "slop")
        if not os.path.isfile(binary):
            raise RuntimeError(f"packaged slop binary is missing: {binary}")

        runner = self._runner()
        api_test = os.path.join(self.cpp.build.bindir, "test_slop_api")
        self.run(
            self._command(runner, api_test),
            env="conanrun",
        )

        script = os.path.join(self.source_folder, "test_cli.py")
        self.run(
            self._command(
                [shutil.which("python3") or "python3"],
                script,
                *runner,
                binary,
            ),
            env="conanrun",
        )

        self._verify_ohos_elf(binary)

    @staticmethod
    def _command(prefix, *arguments):
        values = [*prefix, *arguments]
        return " ".join(f'"{value}"' for value in values)

    def _runner(self):
        machine = platform.machine().lower()
        if machine in ("aarch64", "arm64"):
            return []
        emulator = shutil.which("qemu-aarch64")
        prefix = os.environ.get("QEMU_LD_PREFIX")
        if not emulator or not prefix:
            raise RuntimeError(
                "AArch64 execution requires qemu-aarch64 and QEMU_LD_PREFIX"
            )

        library_paths = []
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                if os.path.isdir(libdir) and libdir not in library_paths:
                    library_paths.append(libdir)

        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        compiler = executables.get("cpp") or executables.get("c")
        if compiler:
            llvm_root = os.path.dirname(os.path.dirname(compiler))
            runtime = os.path.join(
                llvm_root,
                "lib",
                "aarch64-linux-ohos",
            )
            if os.path.isdir(runtime):
                library_paths.append(runtime)

        runner = [
            emulator,
            "-L",
            prefix,
            "-E",
            f"LD_LIBRARY_PATH={':'.join(library_paths)}",
        ]
        preload = os.environ.get("QEMU_OHOS_PRELOAD")
        if preload:
            runner.extend(["-E", f"LD_PRELOAD={preload}"])
        return runner

    def _verify_ohos_elf(self, binary):
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not readelf:
            raise RuntimeError("readelf is required for the OHOS ELF test")
        header = subprocess.run(
            [readelf, "-h", binary],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        dynamic = subprocess.run(
            [readelf, "-d", binary],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if "AArch64" not in header:
            raise RuntimeError("slop is not an AArch64 ELF")
        for forbidden in ("libGL.so", "libGLX.so", "libGLEW.so"):
            if forbidden in dynamic:
                raise RuntimeError(f"unexpected GLX dependency: {forbidden}")
        self.output.info("HarmonyOS ELF contract: PASS")
