#!/usr/bin/env python3
"""Conan recipe for perl-file-remove 1.61 (pure Perl module).

File::Remove — remove files and directories (remove/rm/clear; recursive
directory removal like rm -rf).  Pure Perl (lib/File/Remove.pm), built with
Perl ExtUtils::MakeMaker (perl Makefile.PL && make).

Runtime deps: only perl core modules (Cwd / File::Glob / File::Path /
File::Spec / constant / strict / vars / warnings) -> no conan requires
(root layer has no external dependency).

Package layout mirrors the ecosystem perl-site-lib convention:
  <pkg>/lib/perl5/File/Remove.pm
PERL5LIB injected via runenv_info + buildenv_info (no bin/ -> no commands.json).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class PerlFileRemoveConan(ConanFile):
    name = "perl-file-remove"
    version = "1.61"
    description = "File::Remove - remove files and directories (remove/rm/clear, recursive removal)"
    license = "Perl"  # Same terms as the Perl 5 programming language system itself
    homepage = "https://metacpan.org/dist/File-Remove"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)  # no-op when patches: {}
        # Pure Perl module: ExtUtils::MakeMaker flow
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install .pm tree to <pkg>/lib/perl5 (ecosystem perl site-lib layout)
        src_lib = os.path.join(self.source_folder, "lib")
        dst_lib = os.path.join(self.package_folder, "lib", "perl5")
        if os.path.isdir(src_lib):
            shutil.copytree(src_lib, dst_lib, dirs_exist_ok=True)

    def package_info(self):
        # Pure Perl: nothing to link; expose the .pm dir via PERL5LIB
        self.cpp_info.libs = []
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
