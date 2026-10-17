#!/usr/bin/env python3
"""Consumer test for the packaged ptask executable.

ptask is a GTK+ 3 desktop application; HarmonyOS PC has no X server, so
the test drives the installed binary through the headless paths the
adaptation provides: --version/--help (upstream CLI contract), --selftest
(23 programmatic checks over the production pstr/ptime helpers and the
complete taskwarrior import path) and the expected no-display failure,
which proves GTK is really loaded and initialised by the packaged binary.

The test always runs the shell harness (no can_run guard): CI's
destructive negative gate (L1e) moves the package artifacts away and
re-runs this test, which must then fail because the binary it invokes is
gone.
"""
import os
import shutil

from conan import ConanFile


class PtaskTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "test_ptask.sh"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["ptask"].package_folder
        executable = os.path.join(package_folder, "bin", "ptask")
        script = os.path.join(self.source_folder, "test_ptask.sh")
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.isfile(shell):
            shell = shutil.which("bash") or shutil.which("sh") \
                or "/system/bin/sh"
        self.run(
            f'"{shell}" "{script}" "{executable}" "{package_folder}"',
            env="conanrun",
        )
