#!/usr/bin/env python3
"""Conan recipe — divxcomp 0.1 (pure Perl/Tk GUI script).

divxcomp is a single-file Perl/Tk GUI script (DivX bitrate calculator,
upstream 2003, sole release 0.1, distributed via the Debian pool). There
is no build system and nothing to compile. build() applies the portability
patch and sanity-checks the unpacked source; package() installs the script
as bin/divxcomp and rewrites its shebang to the target environment's Perl
interpreter (OHOS has no /usr/bin/perl, see knowledge E037).

Runtime dependencies on the target: a Perl interpreter (system Perl) and,
for the GUI, Perl::Tk + an X11 display. The GUI stack is not available on
headless OHOS; patches/0001 adds a --version entry point that works
headless and is what test_package exercises.
"""
import os
import stat

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file
from conan.tools.layout import basic_layout


class DivxcompConan(ConanFile):
    name = "divxcomp"
    version = "0.1"
    description = "Bitrate calculator for DivX movies (Perl/Tk GUI script)"
    license = "GPL-2"
    homepage = "https://salsa.debian.org/debian/divxcomp"
    url = "https://salsa.debian.org/debian/divxcomp"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def build(self):
        # Nothing to compile — pure Perl single script, no build system.
        # NOTE: `perl -c` is intentionally NOT run here: the script does
        # `use Tk` at compile time and Perl::Tk (GUI-only dependency) is not
        # installed on headless OHOS, so even a syntax check would fail for
        # environmental, not code, reasons. Headless validation happens in
        # test_package via the patched-in --version flag.
        apply_conandata_patches(self)
        script = os.path.join(self.source_folder, "divxcomp.pl")
        if not os.path.isfile(script) or os.path.getsize(script) == 0:
            raise ConanException("divxcomp.pl missing from source archive")

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        # Install the script as bin/divxcomp (the name Debian uses).
        copy(self, "divxcomp.pl", src=self.source_folder, dst=bin_dir)
        target = os.path.join(bin_dir, "divxcomp")
        os.rename(os.path.join(bin_dir, "divxcomp.pl"), target)
        # OHOS has no /usr/bin/perl (E037): rewrite the shebang to the
        # target environment's Perl interpreter.
        replace_in_file(
            self, target, "#!/usr/bin/perl -w", "#!/data/service/hnp/bin/perl -w", strict=False
        )
        os.chmod(target, os.stat(target).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        # Ship the license text and docs that come with the source.
        copy(self, "GPL.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "divxcomp"), keep_path=False)
        copy(self, "ChangeLog", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "divxcomp"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
