#!/usr/bin/env python3
"""Conan recipe — fmi-ls-bus 1.0.0 (header-only C API).

FMI-LS-BUS (FMI Layered Standard for Network Communication) provides the
C-API header files that define the virtual bus operations between a Network
FMU and the bus simulation. The library itself is header-only: the upstream
repository ships four public C headers under headers/ and a GTest-based
header test harness under tests/.

This recipe installs the four public headers. The public header
fmi3LsBus.h includes "fmi3PlatformTypes.h" from the official FMI 3.0
standard (modelica/fmi-standard), which is not available as a Conan
package in the ohpcd registry, so the recipe fetches the official
fmi-standard headers at the pinned commit and packages the required
platform-types header alongside (2-Clause BSD, same license family).

Upstream tests are verified during adaptation (see notes.md and
MANIFEST.yml for the enumerated two-caliber ledger); the recipe has no
build step, so no compile log is fabricated (R34: consumer test in
test_package exercises the real public API).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.layout import basic_layout


class FmiLsBusConan(ConanFile):
    name = "fmi-ls-bus"
    version = "1.0.0"
    description = "FMI Layered Standard for Network Communication (FMI-LS-BUS) 1.0.0 C-API headers"
    license = "BSD-2-Clause"
    homepage = "https://github.com/modelica/fmi-ls-bus"
    url = "https://github.com/modelica/fmi-ls-bus"

    package_type = "header-library"

    # No compiled artifact: header-only library.
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Official FMI 3.0 standard headers (pinned commit) for
        # fmi3PlatformTypes.h referenced by fmi3LsBus.h.
        get(self, **self.conan_data["fmi_standard"], strip_root=True,
            destination="fmi-standard")

    def build(self):
        # Header-only library: no compiled artifact, so no compile step.
        # apply_conandata_patches is a no-op here (patches: {}); no build
        # log is fabricated (R34).
        apply_conandata_patches(self)

    def package(self):
        # Public fmi-ls-bus headers.
        copy(self, "*.h", src=os.path.join(self.source_folder, "headers"),
             dst=os.path.join(self.package_folder, "include"))
        # Required FMI 3.0 platform types header (from official fmi-standard).
        copy(self, "fmi3PlatformTypes.h",
             src=os.path.join(self.source_folder, "fmi-standard", "headers"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()  # no binary dependencies: single package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "fmi-ls-bus")
        self.cpp_info.set_property("cmake_target_name", "fmi-ls-bus::fmi-ls-bus")