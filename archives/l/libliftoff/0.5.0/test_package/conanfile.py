#!/usr/bin/env python3
"""Conan test_package — libliftoff 0.5.0 L1 test.

Builds and runs a consumer that drives the installed library through its public
API: it opens a (nonexistent) DRM device and walks libliftoff's device/output/
layer objects, which exercises the lazy-init state machine and the version
introspection without needing real hardware.

A device node is deliberately absent here (HarmonyOS PC ships no /dev/dri — see
../notes.md), so this test covers the API contract and the failure path rather
than an actual plane commit; the upstream unit suite, which runs against a mock
libdrm, covers the allocation logic itself during `conan create`.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibliftoffTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "PkgConfigDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = MesonToolchain(self)
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def test(self):
        if not can_run(self):
            return
        executable = os.path.join(self.cpp.build.bindirs[0], "test_libliftoff")
        self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)
