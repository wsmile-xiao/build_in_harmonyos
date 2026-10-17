#!/usr/bin/env python3
"""Conan test_package — kicad-library-symbols 10.0.5 consumer validation.

Data-integrity test (no compile/link): verifies the symbol libraries, the
global sym-lib-table and the SPICE simulation model actually installed in
the package folder. Handles both upstream install modes: packed
``.kicad_sym`` files (KICAD_PACK_SYM_LIBRARIES=ON) and unpacked
``.kicad_symdir`` directory trees (KICAD_PACK_SYM_LIBRARIES=OFF).
"""
import os
import sys

from conan import ConanFile
from conan.tools.cmake import cmake_layout


class KicadLibrarySymbolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def test(self):
        package_folder = self.dependencies["kicad-library-symbols"].package_folder
        validator = os.path.join(self.source_folder, "validate_data.py")
        # sys.executable is the interpreter running conan itself, so the
        # validation does not depend on PATH resolution at test time.
        self.run(f'"{sys.executable}" "{validator}" "{package_folder}"')
