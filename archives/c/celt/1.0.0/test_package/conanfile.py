#!/usr/bin/env python3
"""Installed-package consumer for CELT 1.0.0."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class CeltTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # OHOS /tmp is read-only; clang needs a writable temp dir.
            if str(self.settings.os) == "OHOS":
                tmpdir = os.path.join(self.build_folder, "tmp")
                os.makedirs(tmpdir, exist_ok=True)
                os.environ["TMPDIR"] = tmpdir
            celt = self.dependencies["celt"]
            include = celt.cpp_info.includedirs[0]
            libdir = celt.cpp_info.libdirs[0]
            self.run(
                f"clang test.c -o test_celt -I{include} -L{libdir} -lcelt0 -lm",
                env="conanbuild",
            )
            self.run("./test_celt", env="conanrun")
