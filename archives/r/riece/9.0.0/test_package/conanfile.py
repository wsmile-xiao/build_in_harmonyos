#!/usr/bin/env python3
"""Conan test_package for riece 9.0.0."""

import os
import shlex
import shutil

from conan import ConanFile


class RieceTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.recipe_folder, "test_riece.sh")
        # OHOS /system/bin/sh (mksh) cannot execve ELF binaries, so run the
        # harness through bash to be able to invoke the Emacs binary.
        shell = shutil.which("bash") or os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        self.run(f"{shlex.quote(shell)} {shlex.quote(script)}", env="conanrun")
