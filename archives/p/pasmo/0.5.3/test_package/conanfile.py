#!/usr/bin/env python3
"""test_package for pasmo — exercises the packaged assembler binary (R34).

test_pasmo.sh really runs the installed binary: it assembles fixed Z80/8086
programs and compares the produced images byte-for-byte (raw binary, Intel
HEX, Spectrum TAP/TZX/+3DOS, Amsdos and MSX containers), and checks
diagnostics/exit codes, --err, INCLUDE (-I), --nocase and --bracket.  It
fails if the binary is missing or broken (CI L1e sabotages bin/ to prove the
test really needs the package).
"""
import os

from conan import ConanFile


class PasmoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        self.run("{0} test_pasmo.sh".format(shell), env="conanrun")
