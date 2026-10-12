#!/usr/bin/env python3
"""test_package for doas — runs the installed binary the way a user would.

doas has no upstream test suite; the consumer probe exercises the parser
and CLI surface without root: `-C config` syntax validation (good config
accepted, bad config rejected) and the usage banner.
"""
import sys
from pathlib import Path

from conan import ConanFile


class DoasTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # The actual Conan interpreter starts an absolute installed ELF directly.
        # No unverified hard-coded shared bash or account/privilege simulation.
        probe = Path(self.source_folder) / "probe.py"
        self.run(f'"{sys.executable}" "{probe}"', env="conanrun")
        if str(self.settings.os) == "OHOS":
            safety = Path(self.source_folder) / "harmony_safety.py"
            self.run(f'"{sys.executable}" "{safety}"', env="conanrun")
