#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_package for rifiuti — consumer-perspective functional test.

Runs test.sh, which feeds real INFO2 records to the installed `rifiuti`
binary and asserts on every parsed field (index / deletion time / drive /
path / size), on the `-t` delimiter option and on the two error paths.
"""
import os

from conan import ConanFile


class RifiutiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot be relied on to run ELF binaries;
        # wrap the shell script with the platform bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("%s test.sh" % bash, env="conanrun")
