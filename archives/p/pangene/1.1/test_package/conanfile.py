#!/usr/bin/env python3
"""Conan test_package for pangene 1.1.

pangene is a CLI tool (not a library), so the test drives the binary
installed by the final Conan package (never the source tree): version
check plus the upstream README quick-start re-implemented with the
official C4 fixtures (testdata/C4/*.paf, uncompressed — zlib gzopen
reads plain files transparently).
"""
import os
import shutil

from conan import ConanFile


class PangeneTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot exec ELF binaries; use bash
        # (resolved via CONFIG_SHELL or the profile buildenv PATH — no
        # hardcoded machine paths).
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") \
            or "bash"
        script = os.path.join(self.source_folder, "test_pangene.sh")
        self.run(f'"{bash}" "{script}"', env="conanrun")
