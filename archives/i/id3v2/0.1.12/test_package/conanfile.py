#!/usr/bin/env python3
"""Conan test_package for id3v2 0.1.12 — exercises the id3v2 binary.

id3v2 is a CLI tool, so the test runs the packaged binary instead of linking
against a library. test_id3v2.py writes an ID3 tag to a minimal MP3 and reads
it back, verifying id3v2 and the vendored id3lib work end-to-end.
"""
import os

from conan import ConanFile


class Id3v2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate the id3v2 binary in the package's bindirs.
        id3v2 = os.path.join(self.dependencies["id3v2"].cpp_info.bindirs[0], "id3v2")
        test_script = os.path.join(self.source_folder, "test_id3v2.py")
        self.run(f'python3 "{test_script}" "{id3v2}"', env="conanrun")
