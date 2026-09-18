#!/usr/bin/env python3
"""Conan test_package for perl-io-async 0.805 — runs the R34 consumer check.

Runs a Python script that exercises the packaged IO::Async::* modules through
the perl interpreter (same approach as this archive's perl-carp test_package):
all 39 modules must be packaged, the Future-free subset must actually load, and
a real ``IO::Async::Loop->new`` call must succeed.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            raise ConanException("cannot run on this platform")
        pkg = self.dependencies["perl-io-async"].package_folder
        perl5 = os.path.join(pkg, "lib", "perl5")
        if not os.path.isdir(os.path.join(perl5, "IO", "Async")):
            raise ConanException(f"IO/Async modules missing under {perl5}")
        test_script = os.path.join(os.path.dirname(__file__), "test_io_async.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_io_async.py missing: {test_script}")
        self.run(f'{sys.executable} "{test_script}" "{pkg}"', env="conanrun")
