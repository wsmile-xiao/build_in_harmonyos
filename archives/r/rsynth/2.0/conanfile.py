#!/usr/bin/env python3
"""Conan recipe for rsynth 2.0 — text-to-speech synthesis tool (Autotools).

rsynth converts English text to speech audio files (Sun/NeXT .au or raw
16-bit linear) using Klatt/Holmes formant synthesis.  This package builds
and installs the command-line tool `say`.

OHOS adaptation notes:
  * config.guess/config.sub replaced with modern versions (1994 originals
    cannot detect aarch64-unknown-linux-ohos).
  * Makefile.in install rule extended with DESTDIR support (1994 upstream
    Makefile ignored DESTDIR, which Conan's Autotools.install() needs).
  * Audio playback uses the generic "linux" driver (no /dev/dsp on OHOS);
    `say -o file.au "text"` produces audio files without any audio device.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RsynthConan(ConanFile):
    name = "rsynth"
    version = "2.0"
    description = ("rsynth is a small text-to-speech synthesis program; it "
                   "converts English text to speech audio files (.au / raw "
                   "linear) using Klatt/Holmes formant synthesis.")
    license = "0BSD"            # README: "all (I believe) in the public domain"
    homepage = "http://www.speech.cs.cmu.edu/rsynth/"
    url = "https://snapshot.debian.org/archive/debian-archive/20090802T004153Z/debian/pool/non-free/r/rsynth/rsynth_2.0.orig.tar.gz"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)   # --prefix=/  → package/bin/say
        # 1994-era configure only understands --prefix; prune the modern
        # --bindir/--sbindir/--libdir/--includedir/--oldincludedir/--datarootdir
        # flags that AutotoolsToolchain auto-adds (they abort configure).
        for flag in ("--bindir", "--sbindir", "--libdir", "--includedir",
                     "--oldincludedir", "--datarootdir"):
            tc.configure_args = [a for a in tc.configure_args if not a.startswith(flag)]
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream test suite: `make check` runs `./say -W "Hello there"`.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
