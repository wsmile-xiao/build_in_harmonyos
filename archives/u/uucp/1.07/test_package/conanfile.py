#!/usr/bin/env python3
"""test_package for uucp — exercises the packaged binaries on the OHOS device.

test_uucp_ohos.sh really runs the installed Taylor UUCP programs:
  * the -v version banner of every program (fast, config-free paths);
  * an OHOS consumer case that drives the real configuration parser:
    `uuchk -I <tmpdir>/config` with a sysfile/portfile chain written into a
    temporary directory, asserting the spooled configuration is printed and
    the program exits 0;
  * an OS-level assertion that the consumer case runs on the target ARM64
    machine (HarmonyOS PC reports `uname -m` = aarch64).
It fails if any binary is missing or broken (CI L1e sabotages bin/ to prove
this dependency).
"""
import os

from conan import ConanFile


class UucpTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        self.run("{0} test_uucp_ohos.sh".format(shell), env="conanrun")
