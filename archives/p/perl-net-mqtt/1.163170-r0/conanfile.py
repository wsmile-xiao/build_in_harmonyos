#!/usr/bin/env python3
"""Conan recipe — perl-net-mqtt (Pure Perl module).

Build system: perl Makefile.PL + make + make install
This is a pure Perl module with no C/C++ compilation.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlnetmqttConan(ConanFile):
    name = "perl-net-mqtt"
    version = "1.163170-r0"
    description = "Perl modules for MQTT Protocol (http://mqtt.org/)"
    license = "perl"
    homepage = "https://metacpan.org/dist/Net-MQTT"
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

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl module: perl Makefile.PL && make
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)

    def package(self):
        # Install to package folder using DESTDIR
        self.run("make install DESTDIR={}".format(self.package_folder), cwd=self.source_folder)
        # Copy .pm and .pod files to standard lib/ for consumer access
        # Perl installs to data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/
        perllib = os.path.join(self.package_folder, "data", "service", "hnp",
                               "perl.org", "perl_5.42.0", "lib", "site_perl", "5.42.0")
        if os.path.isdir(perllib):
            copy(self, "*.pm", perllib, os.path.join(self.package_folder, "lib"), keep_path=True)
            copy(self, "*.pod", perllib, os.path.join(self.package_folder, "lib"), keep_path=True)
        # Also copy scripts to bin/
        perllibin = os.path.join(self.package_folder, "data", "service", "hnp",
                                 "perl.org", "perl_5.42.0", "bin")
        if os.path.isdir(perllibin):
            copy(self, "*", perllibin, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Pure Perl module — no C libraries
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        # Set PERL5LIB for consumers
        perllib = os.path.join(self.package_folder, "lib")
        self.env_info.PERL5LIB.append(perllib)
