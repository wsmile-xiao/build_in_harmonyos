#!/usr/bin/env python3
"""Conan test_package — UPSE 1.0.0 public C API and CLI tests."""

import os
import platform
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy
from conan.tools.layout import basic_layout


class UpseTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        if os.path.normpath(self.source_folder) != os.path.normpath(
            self.build_folder
        ):
            copy(self, "test_upse.c", self.source_folder, self.build_folder)

    def build(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration(
                "The UPSE consumer test is HarmonyOS-specific"
            )
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = executables.get("c") or shutil.which("clang") or "clang"
        upse = self.dependencies["upse"]
        output = os.path.join(self.build_folder, "test_upse")
        arguments = [cc, "-std=c99", "-O2"]
        for include_dir in upse.cpp_info.includedirs:
            arguments.append("-I" + include_dir)
        arguments.append(os.path.join(self.build_folder, "test_upse.c"))
        for lib_dir in upse.cpp_info.libdirs:
            arguments.append("-L" + lib_dir)
        arguments.extend(["-lupse", "-lm", "-o", output])
        self.run(
            " ".join(shlex.quote(str(argument)) for argument in arguments),
            env="conanbuild",
        )

    def test(self):
        package = self.dependencies["upse"]
        runner = self._runner()
        test_binary = os.path.join(self.build_folder, "test_upse")
        self.run(self._command(runner, test_binary), env="conanrun")

        player = os.path.join(package.package_folder, "bin", "upse123")
        script = os.path.join(self.source_folder, "test_cli.py")
        self.run(
            self._command(
                [shutil.which("python3") or "python3"],
                script,
                *runner,
                player,
            ),
            env="conanrun",
        )
        self._verify_ohos_elf(package)
        self.output.info(
            'HMBS_TEST_PACKAGE_RESULT: {"executed":5,"passed":5,'
            '"failed":0,"skipped":0,"assertions":23}'
        )

    @staticmethod
    def _command(prefix, *arguments):
        values = [*prefix, *arguments]
        return " ".join(shlex.quote(str(value)) for value in values)

    def _runner(self):
        machine = platform.machine().lower()
        if machine in ("aarch64", "arm64"):
            return []
        emulator = shutil.which("qemu-aarch64")
        prefix = os.environ.get("QEMU_LD_PREFIX")
        if not emulator or not prefix:
            raise ConanInvalidConfiguration(
                "AArch64 execution requires qemu-aarch64 and QEMU_LD_PREFIX"
            )

        library_paths = []
        for dependency in self.dependencies.host.values():
            for lib_dir in dependency.cpp_info.libdirs:
                if os.path.isdir(lib_dir) and lib_dir not in library_paths:
                    library_paths.append(lib_dir)
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = executables.get("c") or executables.get("cpp")
        if compiler:
            runtime = os.path.join(
                os.path.dirname(os.path.dirname(compiler)),
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

    def _verify_ohos_elf(self, package):
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not readelf:
            raise ConanInvalidConfiguration("readelf is required for ELF tests")
        player = os.path.join(package.package_folder, "bin", "upse123")
        library = os.path.join(package.package_folder, "lib", "libupse.so.2.0.0")
        header = subprocess.run(
            [readelf, "-h", player],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        dynamic = subprocess.run(
            [readelf, "-d", library],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if "AArch64" not in header:
            raise RuntimeError("upse123 is not an AArch64 ELF")
        if "libz.so" in dynamic:
            raise RuntimeError("libupse unexpectedly depends on a system libz.so")
        if "libupse.so.2" not in subprocess.run(
            [readelf, "-d", player],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout:
            raise RuntimeError("upse123 does not consume packaged libupse")
        self.output.info("HarmonyOS AArch64 ELF contract: PASS (3 assertions)")
