#!/usr/bin/env python3
"""Functional consumer test for packaged NASM commands."""

import os
import shlex
import shutil

from conan import ConanFile


class NasmTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies.build["nasm"].package_folder
        nasm = os.path.join(package_folder, "bin", "nasm")
        ndisasm = os.path.join(package_folder, "bin", "ndisasm")
        flat_input = os.path.join(self.source_folder, "test16.asm")
        elf_input = os.path.join(self.source_folder, "test64.asm")
        flat_output = os.path.join(self.build_folder, "test16.bin")
        elf_output = os.path.join(self.build_folder, "test64.o")
        disassembly = os.path.join(self.build_folder, "test16.dis")
        script = os.path.join(self.source_folder, "test.sh")

        self._run_native(
            " ".join(
                shlex.quote(arg)
                for arg in (
                    self._config_shell(),
                    script,
                    nasm,
                    ndisasm,
                    flat_input,
                    flat_output,
                    disassembly,
                    elf_input,
                    elf_output,
                )
            )
        )

        with open(flat_output, "rb") as handle:
            machine_code = handle.read()
        expected = bytes.fromhex("b8341283c001c3")
        if machine_code != expected:
            raise AssertionError(
                f"flat binary mismatch: {machine_code.hex()} != {expected.hex()}"
            )

        with open(disassembly, "r", encoding="utf-8") as handle:
            listing = handle.read().lower()
        for instruction in ("mov ax,0x1234", "add ax,byte +0x1", "ret"):
            if instruction not in listing:
                raise AssertionError(
                    f"ndisasm output missing {instruction!r}: {listing!r}"
                )

        with open(elf_output, "rb") as handle:
            elf_magic = handle.read(4)
        if elf_magic != b"\x7fELF":
            raise AssertionError(f"ELF64 output has invalid magic: {elf_magic!r}")

    def _run_native(self, command):
        shell = self._config_shell()
        self.run(
            f"{shlex.quote(shell)} -c {shlex.quote(command)}",
            env="conanbuild",
        )

    @staticmethod
    def _config_shell():
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            "/data/service/hnp/bin/bash",
            shutil.which("bash"),
            shutil.which("sh"),
            "/system/bin/sh",
            "/bin/sh",
        ):
            if not candidate:
                continue
            if os.path.isabs(candidate):
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    return candidate
            elif shutil.which(candidate):
                return candidate
        return "sh"
