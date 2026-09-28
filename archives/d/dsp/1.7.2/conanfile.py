#!/usr/bin/env python3
"""Conan recipe for dsp 1.7.2 (Signalsmith Audio), a header-only C++ DSP library.

Upstream ships as a CMake INTERFACE target (`signalsmith-dsp`) with headers
under `include/signalsmith-dsp/` plus forwarding wrappers at the source root.
The package installs the real headers into `include/signalsmith-dsp/` so a
consumer can `#include <signalsmith-dsp/fft.h>` directly.
"""

import os

from conan import ConanFile
from conan.tools.cmake import cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class DspConan(ConanFile):
    name = "dsp"
    version = "1.7.2"
    description = "Signalsmith Audio DSP — header-only C++ library (envelopes, filters, FFT, delay, mixing, rates, spectral)"
    license = "MIT"
    homepage = "https://github.com/Signalsmith-Audio/dsp"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.compiler.cppstd:
            from conan.tools.build import check_min_cppstd

            check_min_cppstd(self, "11")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only library: no compilation is needed, but patches are
        # applied here to satisfy the recipe lifecycle (G1).
        apply_conandata_patches(self)

    def package(self):
        # The real implementation lives in the top-level headers
        # (common.h, curves.h, delay.h, ...) with `./xxx.h` relative
        # includes.  Install them all into include/signalsmith-dsp/ so
        # internal includes resolve within the same directory.
        headers = [
            "common.h", "curves.h", "delay.h", "envelopes.h", "fft.h",
            "filters.h", "mix.h", "perf.h", "rates.h", "spectral.h",
            "windows.h",
        ]
        dst = os.path.join(self.package_folder, "include", "signalsmith-dsp")
        for header in headers:
            copy(self, header, src=self.source_folder, dst=dst)
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "signalsmith-dsp")
        self.cpp_info.set_property("cmake_target_name", "signalsmith-dsp")
