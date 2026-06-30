#!/usr/bin/env python3
"""Conan recipe — perl-net-libresolv 0.03-r2 (Perl XS/C module).

Net::LibResolv is a Perl XS wrapper around libresolv (DNS resolver functions).
On musl/HarmonyOS, res_query and res_search are in libc itself (no separate libresolv).
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlNetLibresolvConan(ConanFile):
    name = "perl-net-libresolv"
    version = "0.03-r2"
    description = "Perl XS wrapper around libresolv (DNS resolver functions)"
    license = "GPL-1.0-or-later OR Artistic-1.0"
    homepage = "https://metacpan.org/dist/Net-LibResolv"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # res_query is in libc on musl

    def layout(self):
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _perl_config(self, key):
        """Get a value from Perl's Config."""
        result = subprocess.run(
            ["perl", "-MConfig", "-e", f"print $Config{{{key}}}"],
            capture_output=True, text=True
        )
        return result.stdout.strip()

    def build(self):
        apply_conandata_patches(self)

        # Detect Perl paths
        scriptdir = self._perl_config("scriptdir")
        archlibexp = self._perl_config("archlibexp")
        xsubpp = os.path.join(scriptdir, "xsubpp")
        privlibexp = self._perl_config("privlibexp")
        typemap = os.path.join(privlibexp, "ExtUtils", "typemap")
        perl_inc = os.path.join(archlibexp, "CORE")
        home = os.path.expanduser("~")

        # Step 1: xsubpp — convert .xs to .c
        xs_file = os.path.join(self.build_folder, "lib", "Net", "LibResolv.xs")
        c_file = os.path.join(self.build_folder, "lib", "Net", "LibResolv.c")
        self.run(f'perl "{xsubpp}" -typemap "{typemap}" "{xs_file}" > "{c_file}"',
                 cwd=self.build_folder)

        # Step 2: Compile .c to .o
        cc = self._perl_config("cc")
        ccflags = self._perl_config("ccflags")
        optimize = self._perl_config("optimize")
        cccdlflags = self._perl_config("cccdlflags")
        obj_file = os.path.join(self.build_folder, "lib", "Net", "LibResolv.o")
        self.run(
            f'{cc} -c -I"{perl_inc}" -I"{home}/usr/local/include" '
            f'{ccflags} {optimize} {cccdlflags} -o "{obj_file}" "{c_file}"',
            cwd=self.build_folder
        )

        # Step 3: Link .o to .so
        lddlflags = self._perl_config("lddlflags")
        # Fix: ld.lld doesn't understand -fstack-protector-strong, use clang as linker
        blib_dir = os.path.join(self.build_folder, "blib", "arch", "auto", "Net", "LibResolv")
        os.makedirs(blib_dir, exist_ok=True)
        so_file = os.path.join(blib_dir, "LibResolv.so")
        # Use -shared without stale lddlflags that reference -fstack-protector-strong
        self.run(
            f'{cc} -shared -L"{home}/usr/local/lib" -o "{so_file}" "{obj_file}"',
            cwd=self.build_folder
        )

    def package(self):
        # Install .pm and .so to package (Perl layout)
        copy(self, "LibResolv.pm",
             src=os.path.join(self.build_folder, "lib", "Net"),
             dst=os.path.join(self.package_folder, "lib", "perl5", "Net"))
        copy(self, "LibResolv.so",
             src=os.path.join(self.build_folder, "blib", "arch", "auto", "Net", "LibResolv"),
             dst=os.path.join(self.package_folder, "lib", "perl5", "auto", "Net", "LibResolv"))
        # Also place .so in top-level lib/ for G4 artifact detection
        copy(self, "LibResolv.so",
             src=os.path.join(self.build_folder, "blib", "arch", "auto", "Net", "LibResolv"),
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # This is a Perl XS module (.so loaded by Perl's DynaLoader)
        self.cpp_info.libs = []  # No standalone library to link against
        self.cpp_info.libdirs = ["lib/perl5/auto/Net/LibResolv"]
