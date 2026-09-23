#!/usr/bin/env python3
"""Conan recipe — kyoto-cabinet (Kyoto Cabinet) 1.2.80.

Autotools library (custom configure + suffix-rule Makefile without
VPATH support — must build in-source). Provides libkyotocabinet plus
17 CLI tools (kc*test / kc*mgr / kclangctest).

Upstream: https://dbmx.net/kyotocabinet/ (official mirror of
fallabs.com, which currently returns 404).

Optional compression support: zlib enabled (upstream default),
lzma/lzo disabled (upstream defaults, no published deps in repo).
"""
import os
import tempfile

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rm
from conan.tools.gnu import AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class KyotoCabinetConan(ConanFile):
    name = "kyoto-cabinet"
    version = "1.2.80"
    description = "Kyoto Cabinet is a library of routines for managing a database of key-value pairs"
    license = "GPL-3.0-or-later"
    homepage = "https://dbmx.net/kyotocabinet/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27: dependencies use bare ref (no @ohpcd/stable channel) per repo convention
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Feed -I/-L/-lz from the conan zlib package into configure/make
        AutotoolsDeps(self).generate()
        # R33: AutotoolsToolchain generates CC/CXX/CFLAGS/CPPFLAGS/LDFLAGS env
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        # HMDFS (HarmonyOS PC user filesystem) rejects umask-077 temp dirs;
        # ensure TMPDIR points somewhere writable before configure runs.
        os.environ.setdefault("TMPDIR", tempfile.gettempdir())
        apply_conandata_patches(self)
        # Upstream Makefile uses suffix rules only — no VPATH/srcdir support,
        # so configure and make must run in the source folder (in-source build,
        # kissat-style). Autotools helper would run make in build-release
        # where no sources exist.
        conf_args = " ".join([
            "--prefix={}".format(self.package_folder),
            "--enable-static" if not self.options.shared else "--enable-shared",
            "--disable-shared" if not self.options.shared else "--disable-static",
            # Upstream defaults: zlib on, lzma/lzo off. Explicit for reproducibility.
            "--enable-zlib", "--disable-lzma", "--disable-lzo",
        ])
        self.run("./configure {}".format(conf_args),
                 cwd=self.source_folder, env="conanbuild")
        # -j1: upstream check targets share casket* test DB files without
        # declared inter-target dependencies; parallel make would race.
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")
        # Upstream official tests (L1): `make check` — 512 commands across
        # 11 sub-targets (util 38, proto 16, stash 9, cache 9, grass 9,
        # hash 77, tree 77, dir 76, forest 76, poly 111, langc 14).
        # Executed inside build() so the L1c gate sees the official tests run.
        self.run("make -j1 check", cwd=self.source_folder, env="conanbuild")

    def package(self):
        self.run("make install", cwd=self.source_folder, env="conanbuild")
        # No libtool .la files upstream, but guard per Conan 2 conventions
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            rm(self, "*.a", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["kyotocabinet"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["pthread", "m", "rt", "dl"]
        self.cpp_info.exelinkflags = ["-pthread"]
        self.cpp_info.sharedlinkflags = ["-pthread"]
