#!/usr/bin/env python3
"""Conan recipe — perl-net-mqtt-simple (pure Perl module, Makefile.PL build system).

Net::MQTT::Simple — Minimal MQTT version 3 interface.
Build: perl Makefile.PL && make && make install
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlnetmqttsimpleConan(ConanFile):
    name = "perl-net-mqtt-simple"
    version = "1.33-r0"
    description = "Minimal MQTT version 3 interface (Net::MQTT::Simple)"
    license = "unknown"  # upstream META.yml declares "unknown"
    homepage = "https://metacpan.org/release/Net-MQTT-Simple"
    url = "https://github.com/Juerd/Net-MQTT-Simple"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl module: use Makefile.PL (ExtUtils::MakeMaker)
        self.run("perl Makefile.PL", env="conanbuild")
        self.run("make", env="conanbuild")

    def package(self):
        # Pure Perl library package — copy .pm module files to lib/
        # Note: bin/mqtt-simple is a convenience CLI tool that requires a running
        # MQTT broker; not included in the library package to keep it pure-library.
        copy(self, "*.pm",
             src=os.path.join(self.build_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # Pure Perl module — no C libraries to link
        # Set up PERL5LIB for consumers
        perl_lib = os.path.join(self.package_folder, "lib")
        self.output.info(f"PERL5LIB: {perl_lib}")
        # No cpp_info.libs for a pure Perl module
