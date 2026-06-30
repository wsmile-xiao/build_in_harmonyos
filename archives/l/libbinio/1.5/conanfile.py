#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Libbinio, libbinio, 1.5, libbinio 1.5, MIT,
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibbinioConan(ConanFile):
    name = "libbinio"
    version = "1.5"
    description = "Binary I/O stream class library"
    license = "LGPL-2.1"
    homepage = "https://adplug.github.io/libbinio"
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
        tc.extra_ldflags.append("-static")
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
        # ncurses: tc.configure_args.append("--without-shared")  # R4
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Update config.guess/config.sub for HarmonyOS platform support (E007)
        import shutil, glob
        am_dirs = sorted(glob.glob("/storage/Users/currentUser/usr/local/share/automake-*"), reverse=True)
        for am_dir in am_dirs:
            cg_src = os.path.join(am_dir, "config.guess")
            cs_src = os.path.join(am_dir, "config.sub")
            if os.path.exists(cg_src) and os.path.exists(cs_src):
                for dest_dir in [self.source_folder, self.build_folder]:
                    if os.path.isdir(dest_dir):
                        for src, name in [(cg_src, "config.guess"), (cs_src, "config.sub")]:
                            dst = os.path.join(dest_dir, name)
                            if os.path.exists(dst):
                                shutil.copy2(src, dst)
                                os.chmod(dst, 0o755)
                self.output.info(f"Updated config.guess/config.sub from {am_dir}")
                break
        # Fix umask 077 issue in configure script for HMDFS compatibility
        # config.status uses umask 077 to create temp dirs, but HMDFS doesn't
        # allow writing to 700-permission directories
        for dest_dir in [self.source_folder, self.build_folder]:
            cfg = os.path.join(dest_dir, "configure")
            if os.path.exists(cfg):
                with open(cfg, 'r') as f:
                    content = f.read()
                if 'umask 077' in content:
                    content = content.replace('umask 077', 'umask 022')
                    with open(cfg, 'w') as f:
                        f.write(content)
                    self.output.info("Patched configure: umask 077 -> 022")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["binio"]
        self.cpp_info.includedirs = ["include"]
