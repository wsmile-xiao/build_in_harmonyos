#!/usr/bin/env python3
"""Conan recipe — chadwick 0.10.0 (Autotools).

R26: Static linking for terminal tools.
E007: config.guess/config.sub patched for HarmonyOS.
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ChadwickConan(ConanFile):
    name = "chadwick"
    version = "0.10.0"
    description = "Chadwick baseball scoring/scorekeeping tools"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/chadwickbureau/chadwick"
    url = ""  # CI fills this

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
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        tc.extra_ldflags.append("-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # E007: Fix config.guess/config.sub for HarmonyOS
        self._fix_config_guess(src)
        # Fix umask 077 → 022 (HMDFS SGID permission issue)
        self._fix_umask(src)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["chadwick"]

    def _fix_config_guess(self, src):
        """Replace config.guess/config.sub with system versions that support HarmonyOS."""
        candidates = []
        for prefix in [os.path.expanduser("~/usr/local"), "/usr/local", "/usr"]:
            candidates.extend(glob.glob(os.path.join(prefix, "share", "automake-*", "config.guess")))
        for cg_path in sorted(candidates, reverse=True):
            cs_path = cg_path.replace("config.guess", "config.sub")
            if os.path.isfile(cg_path) and os.path.isfile(cs_path):
                am_dir = os.path.dirname(cg_path)
                cg_dst = os.path.join(src, "config.guess")
                cs_dst = os.path.join(src, "config.sub")
                self.run(f'rm -f "{cg_dst}" "{cs_dst}"')
                self.run(f'cp "{cg_path}" "{cg_dst}"')
                self.run(f'cp "{cs_path}" "{cs_dst}"')
                self.run(f'chmod +x "{cg_dst}" "{cs_dst}"')
                self.output.info(f"config.guess/config.sub replaced from {am_dir}")
                return
        self.output.warning("Could not find system config.guess/config.sub to replace")

    def _fix_umask(self, src):
        """Fix umask 077 → 022 in autotools scripts (HMDFS SGID permission issue).

        On HarmonyOS HMDFS, directories created with umask 077 inherit SGID
        from parent, resulting in drwx--S--- which blocks file creation.
        """
        for cfg in ["configure", "config.status", "config.guess", "config.sub"]:
            fpath = os.path.join(src, cfg)
            if os.path.isfile(fpath):
                self.run(f"sed -i 's/umask 077/umask 022/g' '{fpath}' 2>/dev/null || true")
                self.output.info(f"Fixed umask in {cfg}")
