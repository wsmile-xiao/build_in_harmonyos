#!/usr/bin/env python3
"""Conan recipe — arduino-mk 1.6.0 (Arduino-Makefile)

This is a pure Makefile/script package (no C/C++ code to compile).
It installs .mk include files, Python utility scripts, man pages,
and example sketches for command-line Arduino development.

Homepage: https://github.com/sudar/Arduino-Makefile
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class ArduinomkConan(ConanFile):
    name = "arduino-mk"
    version = "1.6.0"
    description = "Makefile and scripts for compiling Arduino sketches from the command line"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/sudar/Arduino-Makefile"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # R38: This is a command-line tool package (scripts), not a library
    package_type = "application"

    # OHOS profile requires all four settings
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches from conandata.yml (none for this version, but structure required)
        apply_conandata_patches(self)
        # Nothing to compile — this is a pure Makefile/script package

    def package(self):
        # Install .mk files and arduino-mk-vars.md to share/arduino/
        copy(self, "*.mk", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "arduino"))
        copy(self, "arduino-mk-vars.md", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "arduino"))

        # Install executables to bin/
        copy(self, "ard-reset-arduino", src=os.path.join(self.source_folder, "bin"), dst=os.path.join(self.package_folder, "bin"))
        copy(self, "robotis-loader", src=os.path.join(self.source_folder, "bin"), dst=os.path.join(self.package_folder, "bin"))

        # Install man pages to share/man/man1/
        copy(self, "ard-reset-arduino.1", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "robotis-loader.1", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"))

        # Install licence
        copy(self, "licence.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc", "arduino-mk"))

        # Install examples
        examples_dir = os.path.join(self.source_folder, "examples")
        if os.path.isdir(examples_dir):
            for root, dirs, files in os.walk(examples_dir):
                rel = os.path.relpath(root, self.source_folder)
                dst_dir = os.path.join(self.package_folder, "share", "doc", "arduino-mk", rel)
                for f in files:
                    if f == ".gitignore":
                        continue
                    src_file = os.path.join(root, f)
                    os.makedirs(dst_dir, exist_ok=True)
                    shutil.copy2(src_file, dst_dir)

    def package_info(self):
        # Scripts are in bin/
        self.cpp_info.bindirs = ["bin"]
        # .mk files and docs are in share/arduino/
        self.cpp_info.resdirs = ["share"]
