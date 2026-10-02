#!/usr/bin/env python3
"""Conan test_package — trickle 1.08 executable consumer test.

Runs the real packaged binaries via a python driver (test_trickle.py):
- trickle -V        -> prints "version 1.08", exit code 1 (upstream errx)
- trickle -h        -> usage on stderr, exit code 1
- trickle (no args) -> usage, exit code 1
- trickled -h       -> usage, exit code 1
- tricklectl -h     -> usage, exit code 1
- packaged LD_PRELOAD modules exist: lib/trickle/trickle-overload.so,
  lib/trickle/libtrickle.so

Safety: only argument-parsing entry points are exercised; no socket
creation (trickled is not started), no LD_PRELOAD launch of child
programs, no network traffic. Standalone shaping (trickle -s ...) is
left to on-device shadow CI validation.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class TrickleTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["trickle"].package_folder
        bins = {b: os.path.join(pkg, "bin", b)
                for b in ("trickle", "trickled", "tricklectl")}
        for name, path in bins.items():
            if not os.path.isfile(path):
                raise ConanException(f"missing packaged executable: {path}")
        for mod in ("trickle-overload.so", "libtrickle.so"):
            mod_path = os.path.join(pkg, "lib", "trickle", mod)
            if not os.path.isfile(mod_path):
                raise ConanException(f"missing LD_PRELOAD module: {mod_path}")
        if not can_run(self):
            self.output.info("cross build: binaries present; runtime validated on OHOS device")
            return
        script = os.path.join(self.source_folder, "test_trickle.py")
        self.run(f'"{sys.executable}" "{script}" '
                 f'"{bins["trickle"]}" "{bins["trickled"]}" "{bins["tricklectl"]}"',
                 env="conanrun")
