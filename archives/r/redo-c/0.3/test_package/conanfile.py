#!/usr/bin/env python3
"""Consumer test for redo-c 0.3 — runs the redo build system end-to-end.

test.sh lays down a tiny .do-file project in a temp dir, builds a target with
the installed `redo` binary, and verifies the produced file content (R34: must
actually exercise the package's executable with observable results).
"""
import os

from conan import ConanFile


class RedoCCTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")