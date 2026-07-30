#!/usr/bin/env python3
"""Conan test_package for nvimpager 0.14.0 — smoke test.

nvimpager -v and -h both exit before invoking neovim, so the installed script
can be tested without neovim installed. This test verifies the packaged script
is functional and reports the expected version.
"""
from conan import ConanFile


class NvimpagerTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run('cd "%s" && bash test.sh' % self.source_folder, env="conanrun")
