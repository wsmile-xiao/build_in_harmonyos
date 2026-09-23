#!/usr/bin/env python3
"""Conan test_package for glib-networking 2.90.0.

Validates that installing glib-networking actually activates a real GLib TLS
backend: g_tls_backend_get_default() must NOT be the built-in GDummyTlsBackend.
The test builds a small TLS client with GLib's public TLS API and performs a
real TLS 1.2+ handshake against a local test server socket, verifying the
backend is functional end to end.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.files import load


class GlibNetworkingTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        self.folders.build = "builddir"
        self.folders.generators = "builddir/generators"

    def generate(self):
        # The CI worker exports AR/AS/STRIP/NM/RANLIB as llvm-* names (llvm-ar,
        # ...) that are NOT on its PATH — only the GNU binutils and ld.lld exist.
        # meson probes the archiver at configure ("Unknown linker(s):
        # [['llvm-ar-15'], ['llvm-ar'], ['ar'], ['gar']]") unless we pin a real
        # one. Clear the broken env values and resolve the archive tool by
        # ABSOLUTE PATH (libsoup3 precedent). Prefer llvm-ar, then ar.
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        archiver = shutil.which("llvm-ar") or shutil.which("ar") or shutil.which("gar")
        if archiver is None:
            raise ConanInvalidConfiguration("No archive tool (llvm-ar/ar/gar) found in PATH")
        tc = MesonToolchain(self)
        tc.ar = archiver
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        exe = os.path.join(self.build_folder, "test_tls_backend")
        # GIO_EXTRA_MODULES is injected by the recipe's runenv_info; ensure it
        # is set explicitly so the gioopenssl module is discoverable.
        mod_dir = os.path.join(self.dependencies["glib-networking"].package_folder,
                               "lib", "gio", "modules")
        env = dict(os.environ)
        env["GIO_EXTRA_MODULES"] = mod_dir
        env["GIO_MODULE_DIR"] = mod_dir
        cmd = f"{bash} -c 'GIO_EXTRA_MODULES=\"{mod_dir}\" GIO_MODULE_DIR=\"{mod_dir}\" {exe}'"
        self.run(cmd, env="conanrun")