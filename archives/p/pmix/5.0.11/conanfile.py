#!/usr/bin/env python3
"""Conan recipe — pmix 5.0.11 (Autotools).

PMIx: Process Management Interface for Exascale — portable PMI library
for MPI-adjacent process management (https://pmix.org/).

PMIx is NOT a system same-name library (R26 exemption), so dynamic
linking is the default. Conan manages the full dependency chain
(libevent + hwloc).

Platform adaptation (patches/, see notes.md):
- 0001/0002: config.guess/config.sub teach the 2021-01-25 autotools
  scripts about HarmonyOS (aarch64-unknown-linux-ohos) — E007/E072.
- 0001/0003: umask 077 -> 022 in config.guess and the configure-embedded
  config.status template. On HMDFS a 0700 dir created under umask 077 is
  not writable even by its owner (E011), which broke `mktemp -d` temp
  files during configure.
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PmixConan(ConanFile):
    name = "pmix"
    version = "5.0.11"
    description = "Process Management Interface for Exascale — portable PMI library"
    license = "BSD-3-Clause"
    homepage = "https://pmix.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libevent/2.1.12")
        self.requires("hwloc/2.14.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        # Build the pmix_* CLI tools (pmix_info, pevent, ...) for R38 smoke.
        tc.configure_args.append("--enable-pmix-binaries")
        # PMIx configure performs its own dependency detection and does not
        # rely solely on CPPFLAGS/LDFLAGS — point it at the Conan packages.
        tc.configure_args.append(
            "--with-libevent=" + self.dependencies["libevent"].package_folder
        )
        tc.configure_args.append(
            "--with-hwloc=" + self.dependencies["hwloc"].package_folder
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Remove .la files (libtool absolute-path issue on relocated packages)
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)

    def package_info(self):
        self.cpp_info.libs = ["pmix"]
        self.cpp_info.set_property("pkg_config_name", "pmix")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
