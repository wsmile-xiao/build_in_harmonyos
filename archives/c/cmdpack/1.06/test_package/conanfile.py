#!/usr/bin/env python3
"""Functional test_package for cmdpack 1.06."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class CmdpackTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    _programs = (
        "bin2ecm",
        "ecm2bin",
        "bincomp",
        "brrrip",
        "byteshuf",
        "cdpatch",
        "fakecrc",
        "hax65816",
        "pecompat",
        "rels",
        "screamf",
        "uips",
        "vb2rip",
        "wordadd",
    )

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["cmdpack"].package_folder
        bin_dir = os.path.join(package_folder, "bin")
        for program in self._programs:
            path = os.path.join(bin_dir, program)
            assert os.path.isfile(path), f"missing cmdpack executable: {path}"

        if can_run(self):
            script = os.path.join(self.recipe_folder, "test_cmdpack.sh")
            self.run(f'sh "{script}"', env="conanrun")
        else:
            for program in self._programs:
                path = os.path.join(bin_dir, program)
                with open(path, "rb") as binary:
                    header = binary.read(20)
                assert header[:4] == b"\x7fELF", (
                    f"{program} is not an ELF binary: {header[:4]!r}"
                )
                assert header[4] == 2, f"{program} is not ELF64"
                byteorder = "little" if header[5] == 1 else "big"
                machine = int.from_bytes(header[18:20], byteorder)
                assert machine == 183, (
                    f"{program} ELF machine is {machine}, expected AArch64 (183)"
                )
