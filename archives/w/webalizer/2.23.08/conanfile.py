#!/usr/bin/env python3
"""Conan recipe for webalizer 2.23.08 — web server log analysis tool.

webalizer is a CLI application (not a library). It produces:
  - webalizer (main binary)
  - wcmgr (DNS cache manager)
  - webazolver (symlink to webalizer)

Dependencies: gd/2.3.3 (transitively pulls zlib/1.3.1.1, libpng/1.6.58)
Build system: autotools (configure + make)
"""
import os
import re

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class WebalizerConan(ConanFile):
    name = "webalizer"
    version = "2.23.08"
    description = "A web server log file analysis program"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/hyc/webalizer"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gd/2.3.3")

    def layout(self):
        basic_layout(self)
        # webalizer's Makefile doesn't support VPATH/out-of-source builds
        self.folders.build = "."
        self.folders.generators = "conan"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--prefix=/")
        tc.configure_args.append("--disable-dns")
        tc.configure_args.append("--disable-bz2")
        tc.configure_args.append("--disable-geoip")
        tc.generate()
        AutotoolsDeps(self).generate()

    def _set_ld_library_path(self):
        """Extract lib paths from conanautotoolsdeps.sh and set LD_LIBRARY_PATH.

        AutotoolsDeps generates LDFLAGS with -L paths but doesn't set
        LD_LIBRARY_PATH for transitive shared deps (libpng is shared).
        The configure test program can't find libpng16.so at runtime.
        """
        gen_folder = os.path.join(self.build_folder, "conan")
        deps_file = os.path.join(gen_folder, "conanautotoolsdeps.sh")
        if not os.path.isfile(deps_file):
            return
        with open(deps_file) as f:
            content = f.read()
        # Extract -L paths from LDFLAGS export line
        paths = re.findall(r'-L(\S+)', content)
        if paths:
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            all_paths = ":".join(paths + ([existing] if existing else []))
            os.environ["LD_LIBRARY_PATH"] = all_paths

    def build(self):
        apply_conandata_patches(self)
        self._set_ld_library_path()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
