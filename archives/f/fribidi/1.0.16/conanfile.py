#!/usr/bin/env python3
"""Conan recipe for fribidi 1.0.16 — Unicode Bidirectional Algorithm library.

Build system: autotools (configure + make).
Patches: config.guess/config.sub OHOS detection.
Runtime fixes: shebang (E165), umask (E110) handled in build().
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class FribidiConan(ConanFile):
    name = "fribidi"
    version = "1.0.16"
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
            replace_in_file(self, configure_path, "umask 077", "umask 002")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["fribidi"]
        self.cpp_info.includedirs = ["include"]
