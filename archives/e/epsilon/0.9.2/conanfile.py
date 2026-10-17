#!/usr/bin/env python3
"""
Conan recipe for epsilon v0.9.2 — OHOS (OpenHarmony) aarch64 adaptation.

EPSILON is a wavelet-based open source image compression C library.
It supports multi-threaded and MPI parallel processing.

Build system: autotools (configure + make).
Dependencies: popt >= 1.7 (popt/1.16 from Conan).

Portability patches:
  - config.guess/config.sub replacement for OHOS detection (E007)
  - configure umask/TMPDIR fix for HMDFS setgid compatibility (E097)
"""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class EpsilonConan(ConanFile):
    name = "epsilon"
    version = "0.9.2"
    description = "Wavelet-based open source image compression library with multi-threading and MPI support"
    license = "LGPL-3.0-or-later"
    homepage = "https://sourceforge.net/projects/epsilon-project/"
    url = "https://sourceforge.net/projects/epsilon-project/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("popt/1.16")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsDeps generates the CFLAGS/CPPFLAGS/LDFLAGS/LIBS env vars
        # from the requirements (popt include/lib paths)
        tc = AutotoolsToolchain(self)
        # Static build by default
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Disable MPI and cluster modes (not needed, avoids extra deps)
        tc.configure_args.append("--disable-mpi")
        tc.configure_args.append("--disable-cluster")
        # Ensure TMPDIR is set so config.status mktemp works on HMDFS (E097)
        if not os.environ.get("TMPDIR"):
            tc.buildenv_vars["TMPDIR"] = os.path.join(
                os.path.dirname(self.build_folder), "tmp"
            )
        tc.generate()
        # Generate dependency flags (popt include/lib paths)
        deps = AutotoolsDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Remove libtool .la files (not needed with Conan)
        rm(self, "*.la", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.libs = ["epsilon"]
        # epsilon also installs command-line tools to bin/
        self.cpp_info.bindirs = ["bin"]
