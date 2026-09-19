#!/usr/bin/env python3
"""Conan test_package for executable package seqprep — runs test.sh."""
import os

from conan import ConanFile


class SeqprepTestConan(ConanFile):
    """test_package for executable packages — runs test.sh which invokes the binary."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # E386: the hnp bash (template default) dies with getcwd() errors on
        # HMDFS test_package dirs; /bin/sh (mksh) is getcwd-clean and runs
        # this POSIX script plus the ELF exec (kernel execve) fine.
        bash = os.environ.get("CONFIG_SHELL", "/bin/sh")
        self.run(f"{bash} test.sh", env="conanrun")
