#!/usr/bin/env python3
"""Conan test_package for pcb2gcode — real end-to-end Gerber -> G-code run.

Consumer-view test for the packaged ``pcb2gcode`` command line tool:

* a HarmonyOS-specific check that the delivered binary is an AArch64/LP64
  little-endian ELF64;
* ``test_pcb2gcode.sh``: runs the tool on a real Gerber sample (a small KiCad
  board, taken from the upstream test data ``tests/data/gerbv_example/backtrack``)
  and validates the produced G-code.

No build is required because pcb2gcode is an application package.
"""
import os
import shutil
import struct
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import mkdir


class Pcb2gcodeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _base_dir(self):
        for attr in ("source_folder", "recipe_folder"):
            base = getattr(self, attr, None)
            if base and os.path.isdir(base):
                return base
        raise ConanException("test_package folder not found")

    def _sub_dir(self, name):
        path = os.path.join(self._base_dir(), name)
        if not os.path.isdir(path):
            raise ConanException("test_package asset not found: {}".format(name))
        return path

    def _check_elf_aarch64(self, path):
        """HarmonyOS-specific check: the delivered binary must be an AArch64
        little-endian ELF64 (OHOS PC is aarch64 / LP64)."""
        with open(path, "rb") as f:
            header = f.read(20)
        assert header[:4] == b"\x7fELF", "not an ELF file: {}".format(path)
        assert header[4] == 2, "not a 64-bit ELF (LP64) binary"          # EI_CLASS
        assert header[5] == 1, "not a little-endian ELF binary"          # EI_DATA
        machine = struct.unpack("<H", header[18:20])[0]
        assert machine == 0xB7, "not an AArch64 binary (e_machine=0x%x)" % machine

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        exe = os.path.join(dep.package_folder, "bin", "pcb2gcode")
        assert os.path.isfile(exe), "pcb2gcode binary not found: {}".format(exe)

        # 1) HarmonyOS PC aarch64 ELF check on the delivered artefact.
        self._check_elf_aarch64(exe)

        # 2) end-to-end Gerber -> G-code conversion, in a scratch directory so
        #    that the recipe folder is not polluted with generated artefacts.
        script = os.path.join(self._base_dir(), "test_pcb2gcode.sh")
        workdir = tempfile.mkdtemp(prefix="pcb2gcode-test-",
                                   dir=os.path.expanduser("~"))
        try:
            mkdir(self, workdir)
            self.run('sh "{}" "{}" "{}" "{}"'.format(
                script, exe, self._sub_dir("data"), workdir), env="conanrun")
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
