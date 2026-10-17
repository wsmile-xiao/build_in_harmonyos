#!/usr/bin/env python3
"""Conan test_package — libvpl 2.16.0 L1 consumer verification.

Builds and runs two consumers against the packaged dispatcher:

* ``test_libvpl``      — generic oneVPL 2.x loader flow (MFXLoad / config /
                         enumeration / session / unload) with API-contract
                         assertions that hold whether or not a runtime is
                         installed.
* ``test_libvpl_ohos`` — HarmonyOS platform assertions: the legacy 1.x
                         dispatcher entry points are present in the shipped
                         ``libvpl.so`` and return defined statuses, and no
                         Intel runtime is enumerated on OHOS.

Both binaries are executed with the ``conanrun`` environment so the dynamic
loader resolves the packaged shared library.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class LibvplTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanException("test_package: no bindirs, binaries were not built")
        for name in ("test_libvpl", "test_libvpl_ohos"):
            exe = os.path.join(bindirs[0], name)
            if not os.path.isfile(exe):
                raise ConanException("test_package: binary not found at %s" % exe)
            self.run('"%s"' % exe, env="conanrun")
