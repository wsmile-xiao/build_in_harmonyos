#!/usr/bin/env python3
"""Conan recipe — libshout 2.4.6 (Autotools).

libshout is the audio streaming library for icecast encoders.
Sources: https://downloads.xiph.org/releases/libshout/libshout-2.4.6.tar.gz

Adaptation notes (see notes.md):
  * config.guess/config.sub updated for HarmonyOS recognition.
  * configure umask 077 → 022 (HMDFS temp-dir permission, E011).
  * PTHREAD_LIBS forced to -lpthread (OHOS pthread_setcancelstate).
  * src/common/thread/thread.c: guard pthread_setcancelstate with __OHOS__.
  * src/icy.c / src/legacy.c: add missing stdlib.h / stdio.h (upstream clang fix).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps

import os


class LibshoutConan(ConanFile):
    name = "libshout"
    version = "2.4.6"
    description = "libshout — audio streaming library for icecast encoders"
    license = "LGPL-2.0"
    homepage = "https://icecast.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_speex": [True, False],
        "with_tls": [True, False],
    }
    default_options = {
        "shared": False,
        "with_speex": True,
        "with_tls": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Core streaming codecs (always needed by libshout)
        self.requires("libogg/1.3.6")
        self.requires("libvorbis/1.3.7")
        # Optional codecs
        if self.options.with_speex:
            self.requires("speex/1.2.1")
        # TLS support (optional, enabled by default)
        if self.options.with_tls:
            self.requires("openssl/3.5.6.1")
        # libtheora is NOT published to ohpcd, so theora support is always disabled.

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps generates .pc files for the Conan-managed dependencies
        # (libogg, libvorbis, speex, openssl) so autotools configure can find
        # them via pkg-config / the CFLAGS/LIBS the toolchain injects.
        pkg = PkgConfigDeps(self)
        pkg.generate()
        tc = AutotoolsToolchain(self)
        # R26: libshout is a system-name library → force static build by default
        # to avoid polluting /lib, /lib64 with libshout.so.
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # libtheora is not published → disable theora support (optional in libshout)
        tc.configure_args.append("--disable-theora")
        # speex driven by option (libshout accepts --disable-speex).
        # TLS (openssl) has no clean --disable-openssl flag; it is auto-detected
        # via the Conan-injected pkg-config environment. To disable TLS, the
        # consumer simply does not require openssl (with_tls=False), and the
        # openssl recipe is not pulled in, so configure won't find it.
        if not self.options.with_speex:
            tc.configure_args.append("--disable-speex")
        # AutotoolsToolchain injects compiler and flags from the Conan
        # toolchain (dependencies' flags), so we never set shell variables
        # directly (R33).
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # The autotools library name is libshout.la → link flag -lshout
        self.cpp_info.libs = ["shout"]
        # libshout needs pthread on OHOS/Linux (thread cancellation, mutexes)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("pthread")
        # The public header is <shout/shout.h>
        self.cpp_info.includedirs = ["include"]
