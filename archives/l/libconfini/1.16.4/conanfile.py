#!/usr/bin/env python3
"""Conan recipe — libconfini 1.16.4 (autotools)

libconfini is a pure-C99 INI/.conf parser with zero external dependencies
(only stdio.h, stdlib.h, stdbool.h, stdint.h). It dispatches parsed nodes
to a user callback instead of storing them.

Upstream: https://github.com/madmurphy/libconfini  (tag 1.16.4)
License:  GPL-3.0-or-later
"""
import glob as _glob
import os as _os

from conan import ConanFile
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibconfiniConan(ConanFile):
    name = "libconfini"
    version = "1.16.4"
    description = "Yet another INI parser — C99 library for parsing INI/.conf files"
    license = "GPL-3.0-or-later"
    homepage = "https://madmurphy.github.io/libconfini/"
    url = "https://github.com/madmurphy/libconfini"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # The bundled config.sub is 2021 vintage and does not recognize the
        # `*-linux-ohos` triplet. libconfini's configure does no OHOS-specific
        # probing, so the musl triplet is accepted and builds identically
        # (verified: libdatrie 0.2.13 uses the same approach and passes).
        # Using a known-good triplet avoids a config.sub patch entirely.
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        # The release tarball ships a pre-generated `configure`, so no
        # autoreconf bootstrap is needed.
        # Fix `umask 077` -> `umask 022` in configure: on the HarmonyOS PC
        # HMDFS-backed filesystem, config.status (which sources `configure`)
        # cannot create its scratch files under 077 umask and the build dies
        # (E011, same root cause recorded for libdatrie/0.2.13).
        for _cfg in _glob.glob(_os.path.join(self.source_folder, "**", "configure"), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        # Remove libtool .la archives: they bake in an absolute libdir
        # (/lib under our prefix=/), which misleads downstream libtool into
        # looking for `//lib/libconfini.la`. Link info is already provided
        # via the .pc file and cpp_info.
        for _la in _glob.glob(_os.path.join(self.package_folder, "lib", "*.la")):
            _os.remove(_la)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["confini"]
        self.cpp_info.set_property("cmake_file_name", "libconfini")
        self.cpp_info.set_property("cmake_target_name", "libconfini::libconfini")
        self.cpp_info.set_property("pkg_config_name", "libconfini")
