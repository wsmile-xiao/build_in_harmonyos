#!/usr/bin/env python3
"""Conan test_package — ondir 0.2.3-git20140220.55279f0 (CLI tool).

Runs test.sh with bash; test.sh really executes the installed ondir binary,
asserts its version/usage behaviour, drives a real enter/leave directory
change through a temporary ~/.ondirrc, and checks the installed
man/example/hook/doc files. Nothing here is a print-only stub (R34).
"""
import os

from conan import ConanFile


class OndirTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries reliably,
        # so wrap the test driver in bash (profile provides CONFIG_SHELL).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.isfile(bash):
            home = os.environ.get("HOME", "")
            brew_bash = os.path.join(home, ".harmonybrew/bin/bash")
            if os.path.isfile(brew_bash):
                bash = brew_bash
            elif os.path.isfile("/bin/bash"):
                bash = "/bin/bash"
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        self.run(f'{bash} test.sh "{pkg_folder}"', env="conanrun")
