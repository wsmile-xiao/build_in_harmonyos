#!/usr/bin/env python3
"""Conan test_package for chordii 4.5.3b.

chordii formats ChordPro text files into PostScript music sheets; a2crd is
the ASCII-to-ChordPro converter shipped alongside. This consumer test:

1. Checks `chordii --version` reports 4.5.3b.
2. Formats the fixed fixture (res/test.cho) into PostScript and verifies the
   output starts with the `%!PS` header.
3. Verifies the formatted sheet contains the song title from the fixture.
4. Runs `a2crd` on the fixture and verifies the chord directives survive
   conversion.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class ChordiiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # VirtualRunEnv adds chordii's bin dir to PATH.
            self.run("chordii --version", env="conanrun")
            res_dir = os.path.join(self.source_folder, "res")
            self.run(
                f'sh "{os.path.join(self.source_folder, "test_chordii.sh")}" '
                f'"{res_dir}"',
                env="conanrun",
            )
