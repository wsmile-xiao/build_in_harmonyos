#!/usr/bin/env python3
"""Conan recipe — dr_mp3 0.7.2 (header-only C library).

dr_mp3 (dr_libs) is a zero-dependency, single-header MP3 decoder written
in portable C89. The official mp3-0.7.2 tag tarball (mackron/dr_libs)
ships dr_mp3.h alongside sibling headers (dr_flac.h / dr_wav.h) and the
upstream CMake test suite.

- This package ships dr_mp3.h only; the sibling formats belong to their
  own packages (dr_wav / dr_flac) per W2 PR atomicity.
- Upstream tests (tests/mp3/*) require the tests/testvectors dataset,
  which is NOT distributed in the official tag tarball (only .gitkeep),
  so no upstream test binaries are built here. Consumer-level functional
  verification is provided by test_package/ (real MPEG1 Layer III frame
  decoded through both the low-level and high-level APIs).
- Consumers compile the implementation into their own binary by defining
  DR_MP3_IMPLEMENTATION before including dr_mp3.h.
"""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class DrMp3Conan(ConanFile):
    name = "dr_mp3"
    version = "0.7.2"
    description = "dr_mp3 is a zero-dependency MP3 audio decoder (single header, portable C89)"
    license = "Unlicense OR MIT"
    homepage = "https://github.com/mackron/dr_libs"
    url = "https://github.com/mackron/dr_libs"
    topics = ("audio", "mp3", "decoder", "header-only", "c")

    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only: 无编译步骤; 应用补丁 (conandata.yml patches 为空时为 no-op)
        apply_conandata_patches(self)

    def package(self):
        copy(self, "dr_mp3.h", self.source_folder,
             os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []  # header-only: implementation compiled into the consumer
