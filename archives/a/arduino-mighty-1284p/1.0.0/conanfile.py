#!/usr/bin/env python3
"""Conan recipe for arduino-mighty-1284p 1.0.0.

Arduino ATmega1284P platform package. This is a header/source-only package
containing Arduino core library headers, bootloader sources, board variant
configurations, and board definitions. The source files are designed for AVR
microcontrollers (ATmega1284P) and are not compiled for the host platform.

The package provides:
  - cores/standard/   — Arduino core library C/C++ source and headers
  - bootloaders/       — optiboot and standard bootloader sources
  - variants/          — pin configuration headers for different board variants
  - boards.txt         — Arduino IDE board definitions

Consumers (e.g., an AVR cross-compiler toolchain) include these headers and
compile the source files for the target AVR device.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class ArduinoMighty1284pConan(ConanFile):
    name = "arduino-mighty-1284p"
    version = "1.0.0"
    description = "Arduino ATmega1284P platform package (cores, bootloaders, variants, board definitions)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/maniacbug/mighty-1284p"
    url = ""  # CI fills this

    # Header-only / source package: no binary artifacts produced
    package_type = "header-library"

    # R32: settings.os check must use in ("Linux", "OHOS") not == "Linux"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external dependencies (W0 pre-check passed)
        pass

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        # Download from official GitHub archive (R39: official source URL)
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # No toolchain needed — this is a header-only package
        pass

    def build(self):
        # Apply patches (none currently, but required by G1 check)
        apply_conandata_patches(self)
        # No compilation step — this is a header/source-only package.
        # Source files are designed for AVR microcontrollers and cannot
        # be compiled for the host (aarch64) platform.
        pass

    def package(self):
        # Package all source files: cores, bootloaders, variants, boards.txt
        # Copy cores/standard/ headers and source
        copy(self, "*", src=os.path.join(self.source_folder, "cores"),
             dst=os.path.join(self.package_folder, "include", "cores"))
        # Copy variant pin configuration headers
        copy(self, "*", src=os.path.join(self.source_folder, "variants"),
             dst=os.path.join(self.package_folder, "include", "variants"))
        # Copy bootloader sources
        copy(self, "*", src=os.path.join(self.source_folder, "bootloaders"),
             dst=os.path.join(self.package_folder, "share", "bootloaders"))
        # Copy board definitions
        copy(self, "boards.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share"))

    def package_info(self):
        # Provide include paths for Arduino core library headers
        # cores/standard/ contains the main Arduino headers (Arduino.h, etc.)
        self.cpp_info.includedirs = [
            os.path.join("include", "cores", "standard"),
        ]
        # No libraries to link — header-only package
        self.cpp_info.libs = []
        # Variant headers (pins_arduino.h) available as resource dirs
        self.cpp_info.resdirs = [
            os.path.join("include", "variants"),
        ]
