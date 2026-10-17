#!/usr/bin/env python3
"""Conan test_package for xfsprogs 7.2.0.

R34: actually executes the packaged tools (version probes via smoke.sh).
R53: HarmonyOS-specific assertions — every tool must be an AArch64 ELF
     (e_machine = 0xB7) and the packaged binaries must run on the device.
"""
import os
import struct

from conan import ConanFile


_BINARIES = ("mkfs.xfs", "xfs_db", "xfs_repair", "xfs_io", "xfs_spaceman")


class XfsprogsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["xfsprogs"].package_folder
        # Conan's AutotoolsToolchain maps sbindir to ${prefix}/bin, so the
        # packaged tools land in bin/.
        sbin = os.path.join(pkg, "bin")

        # R53: every shipped tool must be an AArch64 ELF (e_machine = 0xB7).
        for name in _BINARIES:
            path = os.path.join(sbin, name)
            self.output.info("ELF check: " + path)
            with open(path, "rb") as f:
                header = f.read(20)
            assert header[:4] == b"\x7fELF", name + " is not an ELF binary"
            e_machine = struct.unpack("<H", header[18:20])[0]
            assert e_machine == 0xB7, "%s: e_machine=0x%x, expected AArch64 (0xB7)" % (name, e_machine)

        # R34: execute the packaged tools.
        script = os.path.join(self.source_folder, "smoke.sh")
        self.run('sh "{}" "{}"'.format(script, sbin), env="conanrun")
