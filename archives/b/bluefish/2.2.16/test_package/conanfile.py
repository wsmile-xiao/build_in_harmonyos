#!/usr/bin/env python3
"""Consumer test for the packaged bluefish executable.

bluefish is a GTK3 GUI editor; HarmonyOS PC has no X server, so the test
drives the installed binary through the headless paths the adaptation
provides: --version/--help (upstream CLI contract), --selftest (14
programmatic checks over production bf_lib/libxml2/GLib/GTK code), and the
expected no-display failure that proves GTK is actually loaded and
initialized by the packaged binary.

The test always runs the shell harness (no can_run guard): CI's destructive
negative gate (L1e) moves the package artifacts away and re-runs this test,
which must then fail because the binary it invokes is gone.
"""
import os
import shutil

from conan import ConanFile


class BluefishTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "test_bluefish.sh"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        executable = os.path.join(
            self.dependencies["bluefish"].package_folder, "bin", "bluefish"
        )
        script = os.path.join(self.source_folder, "test_bluefish.sh")
        shell = shutil.which("sh") or "/system/bin/sh"
        self.run(
            f'"{shell}" "{script}" "{executable}"',
            env="conanrun",
        )
