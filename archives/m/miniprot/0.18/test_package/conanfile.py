#!/usr/bin/env python3
"""Conan test_package for miniprot 0.18.

miniprot is a CLI tool (not a library), so the test drives the binary
installed by the final Conan package (never the source tree): version check,
real protein-to-genome alignment on a deterministic synthetic fixture
(PAF + GFF), field/format assertions, and explicit negative inputs.
"""
import os
import shutil

from conan import ConanFile


class MiniprotTestConan(ConanFile):
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
        script = os.path.join(self.source_folder, "test_miniprot.sh")
        self.run(f'"{bash}" "{script}"', env="conanrun")
