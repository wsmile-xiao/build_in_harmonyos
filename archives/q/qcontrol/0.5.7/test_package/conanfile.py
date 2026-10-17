#!/usr/bin/env python3
"""test_package for qcontrol 0.5.7.

Executes the packaged qcontrol binary as a user would: the behavioural
script drives argument parsing, config loading through the embedded Lua
interpreter, command dispatch and the error paths, while the OHOS script
checks the platform specific artefact properties of the shipped ELF.

R34: both scripts invoke the binary from this package and their assertions
decide the exit code, so a missing or broken package fails the test (the CI
L1e destructive check removes the binary and the suite goes red).
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class QcontrolTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        pkg = self.dependencies["qcontrol"].package_folder
        binary = os.path.join(pkg, "bin", "qcontrol")
        share = os.path.join(pkg, "share", "qcontrol")
        # OHOS /system/bin/sh cannot exec ELF binaries: wrap with bash.
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        for script in ("test_qcontrol.sh", "test_ohos.sh"):
            path = os.path.join(self.source_folder, script)
            self.run('"{0}" "{1}" "{2}" "{3}"'.format(
                bash, path, binary, share), env="conanrun")
