#!/usr/bin/env python3
"""Conan consumer checks for the cpipe 3.0.1 application package."""

import json
import os
import platform
import struct

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class CpipeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    @staticmethod
    def _find_file(root, filename):
        for current, _, files in os.walk(root):
            if filename in files:
                return os.path.join(current, filename)
        return None

    @staticmethod
    def _read_elf(path):
        with open(path, "rb") as stream:
            header = stream.read(64)
            if len(header) != 64 or header[:4] != b"\x7fELF":
                raise ConanException(f"not an ELF file: {path}")
            if header[4] != 2 or header[5] != 1:
                raise ConanException(f"expected little-endian ELF64: {path}")

            machine = struct.unpack_from("<H", header, 18)[0]
            phoff = struct.unpack_from("<Q", header, 32)[0]
            phentsize = struct.unpack_from("<H", header, 54)[0]
            phnum = struct.unpack_from("<H", header, 56)[0]
            interpreter = None

            for index in range(phnum):
                stream.seek(phoff + index * phentsize)
                program_header = stream.read(phentsize)
                if len(program_header) < 40:
                    raise ConanException(f"truncated ELF program header: {path}")
                if struct.unpack_from("<I", program_header, 0)[0] != 3:
                    continue
                offset = struct.unpack_from("<Q", program_header, 8)[0]
                size = struct.unpack_from("<Q", program_header, 32)[0]
                stream.seek(offset)
                interpreter = stream.read(size).rstrip(b"\0").decode("ascii")
                break

        return machine, interpreter

    def _assert_aarch64_elf(self, path, require_interpreter=False):
        machine, interpreter = self._read_elf(path)
        if machine != 183:
            raise ConanException(
                f"expected AArch64 ELF (EM_AARCH64=183), got {machine}: {path}"
            )
        if require_interpreter and not (
            interpreter and interpreter.endswith("/ld-musl-aarch64.so.1")
        ):
            raise ConanException(
                f"unexpected HarmonyOS AArch64 interpreter {interpreter!r}: {path}"
            )
        self.output.info(
            f"AArch64 ELF verified: path={path}, e_machine={machine}, "
            f"interpreter={interpreter or 'none'}"
        )

    def test(self):
        dependency = self.dependencies["cpipe"]
        cpipe_bin = os.path.join(dependency.package_folder, "bin", "cpipe")
        probe = self._find_file(self.build_folder, "test_cpipe_ohos")
        if not os.path.isfile(cpipe_bin):
            raise ConanException(f"packaged cpipe binary not found: {cpipe_bin}")
        if not os.access(cpipe_bin, os.X_OK):
            raise ConanException(f"packaged cpipe binary is not executable: {cpipe_bin}")
        if not probe:
            raise ConanException("HarmonyOS compile probe was not built")

        self._assert_aarch64_elf(cpipe_bin, require_interpreter=True)
        self._assert_aarch64_elf(probe, require_interpreter=True)

        runtime_executed = False
        runtime_machine = platform.machine().lower()
        if not cross_building(self) and runtime_machine in ("aarch64", "arm64"):
            self.run(f'"{probe}"', env="conanrun")
            shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run(
                f'"{shell}" test_cpipe_native.sh "{cpipe_bin}"',
                env="conanrun",
                cwd=self.source_folder,
            )
            runtime_executed = True
        else:
            self.output.info(
                "cross-building: AArch64 ELF and HarmonyOS compile checks passed; "
                f"runtime requires an AArch64 HarmonyOS target "
                f"(current machine={runtime_machine})"
            )

        marker = {
            "executed": True,
            "passed": True,
            "runtime_executed": runtime_executed,
            "checks": [
                "packaged_cpipe_aarch64_elf",
                "packaged_cpipe_executable_permission",
                "harmonyos_aarch64_compile_probe",
                "musl_aarch64_interpreter",
            ],
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))

        upstream_marker = {
            "status": "no_tests",
            "framework": "make",
            "command": "make CC=<conan-c-compiler> -j1 cpipe",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "cpipe 3.0.1 upstream tarball has no tests directory, test files, "
                "or check/test target in its raw Makefile"
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker)
        )
