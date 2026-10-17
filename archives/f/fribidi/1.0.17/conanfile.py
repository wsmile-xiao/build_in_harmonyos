#!/usr/bin/env python3
"""Conan recipe for fribidi 1.0.17 — Unicode Bidirectional Algorithm library.

Build system: autotools (configure + make).
Patches:
  - 0001-config.guess.patch: HarmonyOS detection (E007, aarch64-unknown-linux-ohos)
  - 0002-no-help2man-keep-prebuilt-man.patch: drop help2man man-page regeneration
    rule; tarball ships prebuilt fribidi.1 (OHOS workers lack help2man)
Runtime fixes in build(): shebang (E165), umask (E110).
Upstream tests (make check — automake TESTS 4 targets) run inside build()
so conan create log carries real test evidence (CI L1c).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class FribidiConan(ConanFile):
    name = "fribidi"
    version = "1.0.17"
    description = "GNU FriBidi — Unicode Bidirectional Algorithm implementation library"
    license = "LGPL-2.1"
    homepage = "https://github.com/fribidi/fribidi"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os in ("OHOS",):
            configure_path = os.path.join(self.source_folder, "configure")
            # E165: Fix shebang (no /bin/sh on OHOS)
            replace_in_file(self, configure_path, "#! /bin/sh", "#!/system/bin/sh")
            # E110: Fix umask 077→002 for HMDFS temp directory creation
            # (config.status "can't create ./confXXXXXX/subs1.awk: Permission denied")
            replace_in_file(self, configure_path, "umask 077", "umask 002")
        autotools = Autotools(self)
        autotools.configure()
        # -j1: HMDFS does not support mkfifo (FIFO creation) — parallel make fails
        autotools.make(args=["-j1"])
        # Upstream test suite — automake TESTS register 4 targets:
        #   unicode-conformance/BidiTest.txt, BidiCharacterTest.txt (UAX #9 conformance),
        #   run.tests (6 CapRTL/ISO8859-8/UTF-8 charset cases), test-reorder-nsm
        # All run on-device (aarch64 OHOS), evidence lands in conan create log.
        autotools.make(args=["check"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["fribidi"]
        self.cpp_info.includedirs = ["include"]
