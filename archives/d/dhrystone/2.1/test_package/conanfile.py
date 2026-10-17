#!/usr/bin/env python3
"""Conan consumer for the installed Dhrystone CLI and HarmonyOS runtime probe."""

import importlib.util
from pathlib import Path
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class DhrystoneTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["TEST_OHOS"] = str(self.settings.os) == "OHOS"
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        binary = Path(self.dependencies["dhrystone"].package_folder) / "bin/dhrystone"
        if not binary.is_file():
            raise ConanException("installed dhrystone executable is missing")
        script = Path(self.source_folder) / "test_dhrystone.py"
        spec = importlib.util.spec_from_file_location("dhrystone_checks", script)
        checks = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checks)
        if str(self.settings.os) == "OHOS":
            machine, interpreter = checks.elf_interpreter(binary)
            targets = {"armv8": (183, "/lib/ld-musl-aarch64.so.1"),
                       "x86_64": (62, "/lib/ld-musl-x86_64.so.1")}
            if (machine, interpreter) != targets.get(str(self.settings.arch)):
                raise ConanException(f"unexpected HarmonyOS ABI: {machine}, {interpreter}")
            self.output.info(f"HarmonyOS ELF verified: {machine}, {interpreter}")
        if not can_run(self):
            self.output.info("Cross build: ELF verified; runtime tests require the target device")
            return
        environment = Environment()
        if str(self.settings.os) == "OHOS":
            environment.define("DHRYSTONE_TEST_OHOS", "1")
        probes = list(Path(self.build_folder).rglob("test_ohos_runtime"))
        probe_argument = f' --probe "{probes[0]}"' if probes else ""
        with environment.vars(self).apply():
            self.run(f'"{sys.executable}" "{script}" --binary "{binary}"{probe_argument}',
                     env="conanrun")
