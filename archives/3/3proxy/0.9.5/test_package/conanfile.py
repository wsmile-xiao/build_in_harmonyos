#!/usr/bin/env python3
"""test_package for 3proxy 0.9.5 - consumer run of the installed 3proxy binary.

Check 1: usage / version banner of the installed binary.
Check 2: functional smoke - start an HTTP proxy listener on a non-privileged
         loop-back port and open a real TCP connection to it.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class P3ProxyTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building without emulator: test_package skipped")
            return
        shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or shutil.which("sh") or "/bin/sh"
        self.run('"{}" test.sh'.format(shell), env="conanrun")
