#!/usr/bin/env python3
"""Conan recipe — perl-net-pcap 0.21-r2 (Perl XS/C module)

This is a Perl XS module that uses `perl Makefile.PL` (not autotools configure).
It compiles C code (Pcap.xs) into a shared library (Pcap.so) for Perl.

Note: This is a Perl XS module, not a terminal tool. R26 (static linking)
is not applicable for shared library Perl modules. The .so is loaded by Perl
at runtime via DynaLoader.

libpcap is expected to be installed system-wide at /usr/local.
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class PerlnetpcapConan(ConanFile):
    name = "perl-net-pcap"
    version = "0.21-r2"
    description = "Perl interface to pcap packet capture library"
    license = "MIT"
    homepage = "https://metacpan.org/dist/Net-Pcap"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # System-provided dependencies (libpcap installed at ~/usr/local)
    _pcap_lib = os.path.expanduser("~/usr/local/lib")
    _pcap_inc = os.path.expanduser("~/usr/local/include")

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32: OHOS platform compatibility
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"perl-net-pcap does not support os={self.settings.os}"
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
        env.define("LDFLAGS", f"-L{self._pcap_lib}")
        env.append_path("LD_LIBRARY_PATH", self._pcap_lib)
        envvars = env.vars(self)
        envvars.save_script("perl_net_pcap_env")

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # Pass INC and LIBS so Makefile.PL finds libpcap headers and sys/types.h
        # LIBS must be quoted so the shell doesn't split on the space
        self.run(
            f"cd {src} && perl Makefile.PL "
            f"INC=-I{self._pcap_inc} "
            f"'LIBS=-L{self._pcap_lib} -lpcap' "
            f"&& make",
            env=["perl_net_pcap_env"]
        )

    def package(self):
        src = self.source_folder
        # Install using make install
        self.run(
            f"cd {src} && make install DESTDIR={self.package_folder}",
            env=["perl_net_pcap_env"]
        )
        # Copy .so to standard lib/ directory for artifact discovery (G4)
        so_files = glob.glob(os.path.join(src, "blib", "arch", "auto", "Net", "Pcap", "*.so"))
        if so_files:
            copy(self, "*.so", os.path.join(src, "blib", "arch", "auto", "Net", "Pcap"),
                 os.path.join(self.package_folder, "lib"))
        # Copy .pm module file for completeness
        pm_files = glob.glob(os.path.join(src, "blib", "lib", "Net", "*.pm"))
        if pm_files:
            copy(self, "*.pm", os.path.join(src, "blib", "lib", "Net"),
                 os.path.join(self.package_folder, "lib", "Net"))

    def package_info(self):
        self.cpp_info.libs = ["Pcap"]
        self.cpp_info.libdirs = ["lib"]
