#!/usr/bin/env python3
"""Consumer test for the packaged rats executable (R34 / rule12).

RATS is a pure CLI application (no shared library to link), so the consumer
test runs the installed `rats` binary end-to-end against a crafted C sample:

  1) `rats --help` loads and prints usage (validates the signed ELF + runenv).
  2) `rats <insecure.c>` reports at least one vulnerability (validates the
     expat-parsed vulnerability database at DATADIR and the C scanner).
  3) `rats <clean.c>` reports no High/Medium finding (validates the lack of
     false positives on a trivially safe file).

On the Linux build host a cross-compiled OHOS ELF cannot execute, so the
test is skipped via `can_run`. The real execution happens on-device where
`can_run` is True.
"""

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class RatsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "test_rats.sh", "sample.c"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.warning("Cannot run rats in this environment (cross-compiled)")
            return

        executable = os.path.join(
            self.dependencies["rats"].package_folder, "bin", "rats"
        )
        script = os.path.join(self.source_folder, "test_rats.sh")
        shell = shutil.which("sh") or "/system/bin/sh"
        self.run(
            f'"{shell}" "{script}" "{executable}"',
            env="conanrun",
        )
