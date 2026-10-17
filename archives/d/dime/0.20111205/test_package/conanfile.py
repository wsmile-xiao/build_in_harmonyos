#!/usr/bin/env python3
"""Installed-package consumer for dime 0.20111205."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class DimeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # OHOS /tmp is read-only; clang++ needs a writable temp dir.
            if str(self.settings.os) == "OHOS":
                tmpdir = os.path.join(self.build_folder, "tmp")
                os.makedirs(tmpdir, exist_ok=True)
                os.environ["TMPDIR"] = tmpdir
            dime = self.dependencies["dime"]
            include = dime.cpp_info.includedirs[0]
            libdir = dime.cpp_info.libdirs[0]
            tests = [
                # basic write/read round-trip of a LINE entity
                ("test.cpp", "test_dime"),
                # consumer use case: layer table + 3DFACE mesh round-trip
                ("test_model_layers.cpp", "test_model_layers"),
            ]
            for src, exe in tests:
                self.run(
                    f"clang++ {src} -o {exe} -I{include} -L{libdir} -ldime",
                    env="conanbuild",
                )
                self.run(f"./{exe}", env="conanrun")
