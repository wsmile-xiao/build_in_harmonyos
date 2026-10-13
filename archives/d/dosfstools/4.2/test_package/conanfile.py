#!/usr/bin/env python3
"""Consumer test package for dosfstools 4.2.

Runs the packaged tools end to end on a **regular file image**: upstream
mkfs.fat/fsck.fat/fatlabel operate on any seekable file (S_ISREG path), so
no block device and no root privileges are required. The block-device and
mount faces are not part of the deliverable surface on this platform and
are deliberately not asserted here.
"""

import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class DosfstoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindirs = self.dependencies["dosfstools"].cpp_info.bindirs
        if not bindirs:
            raise ConanException("dosfstools reports no bindirs")
        bindir = bindirs[0]
        for tool in ("mkfs.fat", "fsck.fat", "fatlabel"):
            path = os.path.join(bindir, tool)
            if not os.path.isfile(path):
                raise ConanException(f"missing packaged executable: {path}")
        if not can_run(self):
            self.output.info(
                "cross build: packaged executables exist; runtime validation "
                "happens on the HarmonyOS PC device"
            )
            return
        script = os.path.join(self.source_folder, "test_dosfstools.py")
        self.run(f'"{sys.executable}" "{script}" "{bindir}"', env="conanrun")
