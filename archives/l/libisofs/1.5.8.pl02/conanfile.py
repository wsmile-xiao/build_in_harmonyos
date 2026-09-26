#!/usr/bin/env python3
"""Conan recipe for libisofs (libburnia ISO 9660 filesystem creation library)."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibisofsConan(ConanFile):
    name = "libisofs"
    version = "1.5.8.pl02"
    description = "Library to pack up hard disk files and directories into a ISO 9660 disk image"
    license = "GPL-2.0-or-later"
    homepage = "https://dev.lovelyhq.com/libburnia/libisofs"
    url = "https://files.libburnia-project.org/releases/libisofs-1.5.8.pl02.tar.gz"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libisofs is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        # zlib is probed by configure (--enable-zlib, default yes) and the
        # OHOS sysroot provides zlib.h + libz: ZLIB_DEF gets set and the
        # zisofs/gzip filters are compiled into the library. It is a real
        # link-time dependency, so declare it (aligned with the repo
        # convention of zlib/1.3.1.1 binaries).
        # libacl/xattr/libjte/lfa-flags/projid stay at their configure
        # defaults: probed, feature-disabled when missing — see notes.md.
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # a52dec-style OHOS handling: pass an explicit GNU triplet so
        # configure never invokes config.guess (whose output on the OHOS
        # build host is aarch64-unknown-linux-ohos — E160). The config.sub
        # patch (0001) additionally accepts linux-ohos triples for any
        # sub-configure invocation that still gets one.
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # Upstream 1.5.8 ships no active automated test suite: the unit test
        # stanza in Makefile.am is commented out ("needs a volunteer to be
        # rewritten with the current API"). See notes.md and MANIFEST.yml.
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        import glob as _glob
        for _la in _glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.libs = ["isofs"]
        self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.includedirs = ["include", "include/libisofs"]
