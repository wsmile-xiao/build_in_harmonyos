#!/usr/bin/env python3
"""Conan recipe - GNU libxmi 1.2 (autotools, single static library).

The 2001 tarball ships a pre-modern libtool (ltconfig) that cannot handle
the OHOS triplet.  The regenerated bootstrap files (configure, ltmain.sh,
aux scripts, refreshed aclocal.m4/Makefile.in) are pre-built and bundled
in compat/, restored by source(); no runtime autoreconf is needed
(HMDFS invalidates directory handles across autoreconf renames, and CI
workers lack automake/libtool).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain


class LibxmiConan(ConanFile):
    name = "libxmi"
    version = "1.2"
    description = "GNU libxmi - 2D rasterization library converting vector paths to pixels"
    license = "GPL-2.0-or-later"
    homepage = "https://www.gnu.org/software/libxmi/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    exports = "compat/*"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "compat/*", self.recipe_folder,
             os.path.join(self.export_folder, "compat"))

    def layout(self):
        # in-tree build (dominion 2.8.2 / fontutils 0.7 precedent).
        self.folders.source = '.'
        self.folders.build = '.'

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        import shutil
        # locate the exported compat/ (regenerated bootstrap files)
        src = None
        for cand in (os.path.join(self.recipe_folder, "compat"),
                     os.path.join(os.path.dirname(self.recipe_folder), "compat"),
                     os.path.join(self.source_folder, "compat")):
            if os.path.isdir(cand):
                src = cand
                break
        if src:
            for root, dirs, files in os.walk(src):
                rel = os.path.relpath(root, src)
                tgt = self.source_folder if rel == "." else os.path.join(self.source_folder, rel)
                os.makedirs(tgt, exist_ok=True)
                for f in files:
                    shutil.copy2(os.path.join(root, f), os.path.join(tgt, f))
        for f in ("config.guess", "config.sub", "compile", "missing",
                  "depcomp", "install-sh", "configure", "ltmain.sh"):
            path = os.path.join(self.source_folder, f)
            if os.path.exists(path):
                os.chmod(path, 0o755)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # config.guess cannot identify OHOS; pass the triplets explicitly
        # (same approach as argp-standalone).
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # -j1: HMDFS jobserver FIFO creation is not permitted.
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["prefix="])
        # checklist item: libtool archives bake in absolute libdir paths
        la = os.path.join(self.package_folder, "lib", "libxmi.la")
        if os.path.exists(la):
            os.remove(la)

    def package_info(self):
        self.cpp_info.libs = ["xmi"]
