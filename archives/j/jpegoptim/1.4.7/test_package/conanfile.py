#!/usr/bin/env python3
"""Conan test_package for jpegoptim 1.4.7.

jpegoptim is a command-line tool, so the test runs the packaged binary over a
real JPEG and asserts the observable behaviour (R34).  The fixture is written
here rather than by the shell script: the tool has no way to synthesize a
JPEG, and the libjpeg CLI helpers (cjpeg) cannot be executed on OHOS because
their DT_RPATH entries resolve relative to the current directory.
"""
import base64
import os

from conan import ConanFile
from conan.tools.build import can_run

# 16x16 baseline JPEG (SOI, JFIF APP0, COM "HarmonyOS PC", DQT, SOF0, DHTs,
# SOS, EOI) - marker structure checked by test.sh.
FIXTURE_JPG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD//gAOSGFybW9ueU9TIFBD/9sAQwADAgIDAgIDAwMDBAMDBAUI"
    "BQUEBAUKBwcGCAwKDAwLCgsLDQ4SEA0OEQ4LCxAWEBETFBUVFQwPFxgWFBgSFBUU/9sAQwEDBAQF"
    "BAUJBQUJFA0LDRQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQU"
    "FBQU/8AAEQgAEAAQAwEiAAIRAQMRAf/EABUAAQEAAAAAAAAAAAAAAAAAAAkI/8QAFxAAAwEAAAAA"
    "AAAAAAAAAAAAAAhEgf/EABQBAQAAAAAAAAAAAAAAAAAAAAT/xAAUEQEAAAAAAAAAAAAAAAAAAAAA"
    "/9oADAMBAAIRAxEAPwCQF2lwUBdpcC/XaXBQF2lwQO//2Q=="
)


class JpegoptimTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        with open(os.path.join(self.source_folder, "fixture.jpg"), "wb") as f:
            f.write(FIXTURE_JPG)

    def test(self):
        if not can_run(self):
            return
        bindir = self.dependencies["jpegoptim"].cpp_info.bindirs[0]
        jpegoptim = os.path.join(bindir, "jpegoptim")
        fixture = os.path.join(self.source_folder, "fixture.jpg")
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f'sh "{script}" "{jpegoptim}" "{fixture}"', env="conanrun")
