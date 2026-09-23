#!/usr/bin/env python3
"""Conan recipe for Concurrency Kit (ck) 0.7.2 — Autotools.

Upstream `configure` is a hand-written script whose `uname -s` whitelist
lacks HarmonyOS (OHOS PC); the platform patch adds HarmonyOS to the
Linux case (knowledge-graph E160 class fix).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CkConan(ConanFile):
    name = "ck"
    version = "0.7.2"
    description = "Concurrency Kit: concurrency primitives, safe memory reclamation mechanisms and non-blocking data structures"
    license = "BSD-2-Clause"
    homepage = "http://concurrencykit.org"
    url = "https://github.com/concurrencykit/ck"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

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
        # upstream configure is hand-written: unknown options are fatal and
        # --oldincludedir is missing from its compat-ignore list
        tc.update_configure_args({"--oldincludedir": None})
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
        self.cpp_info.libs = ["ck"]
