#!/usr/bin/env python3
"""Conan recipe for libffi 3.4.4 — Autotools (configure + make)."""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibffiConan(ConanFile):
    name = "libffi"
    version = "3.4.4"
    description = "Portable Foreign Function Interface library"
    license = "MIT"
    homepage = "https://github.com/libffi/libffi"
    url = ""  # CI fills this
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # Use local tarball via file:// URL when available (local builds)
        local_tarball = os.path.join(os.path.expanduser("~"), "tmp/builds/libffi-3.4.4.tar.gz")
        src = self.conan_data["sources"]
        if os.path.exists(local_tarball):
            src = {"url": f"file://{local_tarball}", "sha256": src["sha256"]}
        get(self, **src, strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: libffi IS a system same-name library - static only
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--enable-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["ffi"]
