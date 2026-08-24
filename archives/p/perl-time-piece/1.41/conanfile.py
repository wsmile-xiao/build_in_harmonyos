#!/usr/bin/env python3
"""Conan recipe for perl-time-piece 1.41 — Time::Piece module
(pure-Perl, CPAN source, zero runtime dependencies).

Pure-Perl module: build via perl Makefile.PL → make → make install
DESTDIR into the conan package folder; consumers add site/lib to PERL5LIB.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class PerlTimePieceConan(ConanFile):
    name = "perl-time-piece"
    version = "1.41"
    description = "Time::Piece — Object Oriented time objects"
    license = "Artistic-1.0-Perl"
    homepage = "https://metacpan.org/pod/Time::Piece"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "python-require"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        perl = "/data/service/hnp/bin/perl"
        self.run(f'{perl} Makefile.PL', cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)
        staging = os.path.join(self.build_folder, "perl-stage")
        self.run(f'make install DESTDIR="{staging}"', cwd=self.source_folder)

    def package(self):
        staging = os.path.join(self.build_folder, "perl-stage")
        if not os.path.isdir(staging):
            raise ConanException(f"perl staging missing: {staging}")
        for root, _dirs, files in os.walk(staging):
            for f in files:
                src = os.path.join(root, f)
                rel = os.path.relpath(src, staging)
                dst = os.path.join(self.package_folder, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                # XS .so needs read+exec — HMDFS umask may strip perms
                # (0o755 becomes 0o770 on hmdfs, other users can't read —
                # CI runner is "other" → Permission denied; use 0o777)
                if f.endswith(".so"):
                    os.chmod(dst, 0o777)
        # locate Time/Piece.pm (site_perl or lib/perl5 — walk to avoid drift)
        found = None
        for root, _dirs, files in os.walk(self.package_folder):
            if "Piece.pm" in files and os.path.basename(root) == "Time":
                found = root
                break
        if not found:
            raise ConanException("Time/Piece.pm not found in package")

    def package_info(self):
        # expose the perl5 dir containing Time/Piece.pm as PERL5LIB
        site = None
        for root, _dirs, files in os.walk(self.package_folder):
            if "Piece.pm" in files and os.path.basename(root) == "Time":
                site = root
                break
        if site:
            self.output.info(f"PERL5LIB={site}")
