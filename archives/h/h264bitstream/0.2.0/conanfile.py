#!/usr/bin/env python3
"""Conan recipe — h264bitstream 0.2.0 (Makefile)

h264bitstream is a C library for reading and writing H.264 video bitstreams
in Annex B format. Includes the h264_analyze command-line tool.

Build system: simple Makefile (Makefile.unix, no autotools required).
License: LGPL-2.1-or-later
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain


class H264BitstreamConan(ConanFile):
    name = "h264bitstream"
    version = "0.2.0"
    description = "H.264 bitstream parsing library and analysis tool"
    license = "LGPL-2.1-or-later"
    homepage = "https://sourceforge.net/projects/h264bitstream/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Read CC from Conan toolchain env file (R33: avoid bare shell vars in self.run)
        cc = "clang"
        env_path = os.path.join(self.build_folder, "conanautotoolstoolchain.sh")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("export CC="):
                        cc = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        self.run(f'make -f Makefile.unix CC="{cc}" LD="{cc}" -j1')

    def package(self):
        # Copy static library
        copy(self, "libh264bitstream.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        # Copy binary
        copy(self, "h264_analyze", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        # Copy headers (installed to include/h264bitstream/)
        for header in ("h264_stream.h", "h264_sei.h", "h264_avcc.h", "bs.h"):
            copy(self, header, src=self.build_folder,
                 dst=os.path.join(self.package_folder, "include", "h264bitstream"))

    def package_info(self):
        self.cpp_info.libs = ["h264bitstream"]
        self.cpp_info.bindirs = ["bin"]
