#!/usr/bin/env python3
"""Functional test for the packaged AVR Binutils toolchain."""

import os
import shlex
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run


class AvrBinutilsTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    exports_sources = "smoke.S", "smoke.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @property
    def _package_folder(self):
        return self.dependencies["avr-binutils"].package_folder

    def _tool(self, name):
        path = os.path.join(self._package_folder, "bin", name)
        if not os.path.isfile(path):
            raise ConanInvalidConfiguration(
                "Packaged tool was not found: {}".format(path)
            )
        return path

    def _run_capture(self, command):
        result = subprocess.run(
            command,
            cwd=self.build_folder,
            text=True,
            capture_output=True,
            check=True,
        )
        output = result.stdout + result.stderr
        if output.strip():
            self.output.info(output.strip())
        return output

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross-building: packaged OHOS host tools cannot run"
            )
            return

        build = Path(self.build_folder)
        build.mkdir(parents=True, exist_ok=True)
        source = Path(self.source_folder) / "smoke.S"
        obj = build / "smoke.o"
        elf = build / "smoke.elf"
        ihex = build / "smoke.hex"

        assembler = self._tool("avr-as")
        linker = self._tool("avr-ld")
        objcopy = self._tool("avr-objcopy")
        objdump = self._tool("avr-objdump")
        nm = self._tool("avr-nm")
        readelf = self._tool("avr-readelf")
        size = self._tool("avr-size")

        smoke_script = Path(self.source_folder) / "smoke.sh"
        self.run(
            " ".join(
                shlex.quote(str(value))
                for value in (
                    "sh",
                    smoke_script,
                    assembler,
                    linker,
                    objcopy,
                    source,
                    obj,
                    elf,
                    ihex,
                )
            ),
            env="conanrun",
        )

        version = self._run_capture([assembler, "--version"])
        if "2.43.1" not in version:
            raise ConanInvalidConfiguration(
                "Unexpected avr-as version: {}".format(version.splitlines()[0])
            )

        self._run_capture(
            [
                assembler,
                "-mmcu=atmega328p",
                "-o",
                str(obj),
                str(source),
            ]
        )
        self._run_capture(
            [
                linker,
                "-m",
                "avr5",
                "-e",
                "_start",
                "-o",
                str(elf),
                str(obj),
            ]
        )
        self._run_capture(
            [objcopy, "-O", "ihex", str(elf), str(ihex)]
        )

        file_header = self._run_capture([objdump, "-f", str(elf)])
        if "file format elf32-avr" not in file_header:
            raise ConanInvalidConfiguration(
                "avr-objdump did not identify elf32-avr"
            )
        if "architecture: avr" not in file_header:
            raise ConanInvalidConfiguration(
                "avr-objdump did not identify the AVR architecture"
            )

        symbols = self._run_capture([nm, str(elf)])
        if " T _start" not in symbols:
            raise ConanInvalidConfiguration(
                "Linked AVR ELF does not export _start"
            )

        elf_header = self._run_capture([readelf, "-h", str(elf)])
        if "Atmel AVR" not in elf_header:
            raise ConanInvalidConfiguration(
                "avr-readelf did not identify the AVR machine"
            )

        self._run_capture([size, str(elf)])
        if not ihex.read_text(encoding="ascii").startswith(":"):
            raise ConanInvalidConfiguration(
                "avr-objcopy did not create Intel HEX output"
            )
        self.output.info("PASS: packaged AVR Binutils functional smoke test")
