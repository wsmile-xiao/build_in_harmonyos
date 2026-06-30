#!/usr/bin/env python3
"""Conan recipe — perl-net-libidn 0.12-r17 (Perl XS/C module)

This is a Perl XS module that uses `perl Makefile.PL` (not autotools configure).
It compiles C code (LibIDN.xs) into a shared library (LibIDN.so) for Perl.

Note: This is a Perl XS module, not a terminal tool. R26 (static linking)
is not applicable for shared library Perl modules. The .so is loaded by Perl
at runtime via DynaLoader.

libidn is expected to be installed system-wide.
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class PerlnetlibidnConan(ConanFile):
    name = "perl-net-libidn"
    version = "0.12-r17"
    description = "Perl bindings for GNU Libidn"
    license = "LGPL-2.1+"
    homepage = "https://metacpan.org/dist/Net-LibIDN"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # System-provided dependencies (libidn installed at /usr/local)
    _libidn_lib = "/storage/Users/currentUser/usr/local/lib"
    _libidn_inc = "/storage/Users/currentUser/usr/local/include"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32: OHOS platform compatibility
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"perl-net-libidn does not support os={self.settings.os}"
            )

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = Environment()
        env.define("CC", "clang")
        env.define("CFLAGS", "-fPIC -O2")
        env.define("LDFLAGS", f"-L{self._libidn_lib}")
        env.append_path("LD_LIBRARY_PATH", self._libidn_lib)
        envvars = env.vars(self)
        envvars.save_script("perl_net_libidn_env")

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        self.run(
            f"cd {src} && perl Makefile.PL "
            f"--with-libidn={self._libidn_lib} "
            f"--with-libidn-inc={self._libidn_inc} "
            f"&& make",
            env=["perl_net_libidn_env"]
        )

    def package(self):
        src = self.source_folder
        # Install using make install
        self.run(
            f"cd {src} && make install DESTDIR={self.package_folder}",
            env=["perl_net_libidn_env"]
        )
        # Copy .so to standard lib/ directory for artifact discovery (G4)
        so_files = glob.glob(os.path.join(src, "blib", "arch", "auto", "Net", "LibIDN", "*.so"))
        if so_files:
            copy(self, "*.so", os.path.join(src, "blib", "arch", "auto", "Net", "LibIDN"),
                 os.path.join(self.package_folder, "lib"))
        # Copy .pm module file for completeness
        pm_files = glob.glob(os.path.join(src, "blib", "lib", "Net", "*.pm"))
        if pm_files:
            copy(self, "*.pm", os.path.join(src, "blib", "lib", "Net"),
                 os.path.join(self.package_folder, "lib", "Net"))

    def package_info(self):
        self.cpp_info.libs = ["LibIDN"]
        self.cpp_info.libdirs = ["lib"]
