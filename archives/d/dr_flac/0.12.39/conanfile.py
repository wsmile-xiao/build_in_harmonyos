#!/usr/bin/env python3
"""Conan recipe — dr_flac 0.12.39 (single-header / header-only).

dr_flac is a pure-C FLAC audio decoder delivered as a single self-contained
header (dr_flac.h, ~512 KB) inside the mackron/dr_libs multi-header library
collection. The public API is consumed by including "dr_flac/dr_flac.h" and
adding #define DR_FLAC_IMPLEMENTATION to exactly one translation unit. No
separate library artifact is shipped — consumers compile the implementation
themselves (same delivery model as the miniaudio/0.11.25 archive).

Source provenance: the official 0.12.39 has NO git tag (flac-0.12.39 does not
exist in mackron/dr_libs; flac tags start at flac-0.12.43) and no GitHub
release. The proven, verified source is release commit
7d3638f215599e4b576fe5d4be4f6820b9988e48 ("dr_flac: Version 0.12.39",
committed 2022-09-17T07:11:14Z), cross-checked against the in-header banner
"dr_flac - v0.12.39 - 2022-09-17" and DRFLAC_VERSION_MAJOR/MINOR/REVISION.
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class DrFlacConan(ConanFile):
    name = "dr_flac"
    version = "0.12.39"
    package_type = "header-library"

    description = (
        "FLAC audio decoder written in C, delivered as a single self-contained "
        "header (dr_flac.h) from the mackron/dr_libs collection. Decodes raw "
        "FLAC streams (fixed/verified metadata, seekable and non-seekable, "
        "with built-in CRC-8/CRC-16 frame verification). No external "
        "dependencies (libc/libm only)."
    )
    homepage = "https://github.com/mackron/dr_libs"
    license = "MIT-0 OR Unlicense"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("audio", "flac", "decoder", "single-header", "dr-libraries")

    # R32: settings.os judgement must use in ("Linux", "OHOS"); keep all four
    # to pass L0p.
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        # R28 (conan-verify G1): conandata.yml patch section is exported even
        # though no patches are declared for 0.12.39 (header-only, no diff vs
        # the verified release commit). Keeps the recipe on the v3.0 shape.
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        # Header-only / single-header: the package is identical for every build
        # configuration.
        self.info.clear()

    def source(self):
        # GitHub archive of the verified 0.12.39 release commit
        # (dr_libs-7d3638f215599e4b576fe5d4be4f6820b9988e48/ root is stripped).
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # G1 (conan-verify): header-only recipe still declares build(); apply
        # the (empty) conandata patch section for v3.0 shape. No library
        # artifact is compiled — consumers compile dr_flac.h themselves.
        apply_conandata_patches(self)

    def package(self):
        # Install the official single header at the canonical dr_flac layout:
        #   ${CMAKE_INSTALL_INCLUDEDIR}/dr_flac/dr_flac.h
        # matching how the dr_flac upstream tests and consumers include it
        # (#include "dr_flac/dr_flac.h").
        copy(
            self,
            "dr_flac.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include", "dr_flac"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "dr_flac")
        self.cpp_info.set_property("cmake_target_name", "dr_flac::dr_flac")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
