#!/usr/bin/env python3
"""Conan test_package for dev86.

Verifies the 8086 toolchain end-to-end:
1. bcc compiles C to 8086 assembly (-S)
2. as86 assembles the .s into an object file
3. ld86 links the object into an 8086 executable
4. objdump86 analyzes the resulting executable
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class Dev86TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        pass

    def test(self):
        # bcc locates its components (bcc-cpp, bcc-cc1, include) under
        # $BCC_PREFIX/lib/bcc; HMDFS /tmp is read-only, so point TMPDIR at a
        # writable folder (bcc honors TMPDIR thanks to the OHOS patch).
        pkg = self.dependencies["dev86"].package_folder
        workdir = self.build_folder
        tmpdir = os.path.join(workdir, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["BCC_PREFIX"] = pkg
        os.environ["TMPDIR"] = tmpdir

        test_c = os.path.join(self.source_folder, "test.c")
        # R34: exercise the packaged toolchain with real input
        self.run(
            f'bcc -S "{test_c}" -o test.s && '
            f'as86 test.s -o test.o && '
            f'ld86 test.o -o test.elf && '
            f'objdump86 test.elf',
            env="conanrun",
        )
