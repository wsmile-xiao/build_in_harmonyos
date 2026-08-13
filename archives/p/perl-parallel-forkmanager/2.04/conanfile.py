#!/usr/bin/env python3
"""Conan recipe — perl-parallel-forkmanager 2.04 (Pure Perl module).

This is a pure Perl module using ExtUtils::MakeMaker (Makefile.PL).
Build: perl Makefile.PL && make
No C/C++ compilation, no shared libraries.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlParallelForkManagerConan(ConanFile):
    name = "perl-parallel-forkmanager"
    version = "2.04"
    description = "A simple parallel processing fork manager"
    license = "perl_5"
    homepage = "https://metacpan.org/release/Parallel-ForkManager"
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

    def validate(self):
        # R32: settings.os must be in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported os: {self.settings.os}. Only Linux and OHOS are supported."
            )

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl module: perl Makefile.PL && make
        # Must run in source folder where Makefile.PL is located
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Copy Perl module files directly to package_folder/lib/
        # This matches PERL5LIB=package_folder/lib set in package_info()
        copy(
            self,
            "*.pm",
            os.path.join(self.source_folder, "lib"),
            os.path.join(self.package_folder, "lib"),
        )

    def package_info(self):
        # Pure Perl module — no C/C++ libraries
        perl_lib = os.path.join(self.package_folder, "lib")
        self.cpp_info.includedirs = []  # No C/C++ headers
        self.cpp_info.libdirs = []  # No C/C++ libraries
        self.cpp_info.libs = []
        # Set PERL5LIB for consumers
        self.runenv_info.append_path("PERL5LIB", perl_lib)
