#!/usr/bin/env python3
"""Conan recipe for mypager 0.6.3 — a lightweight terminal pager.

The whole package is a single self-contained Perl script (upstream
Makefile only `install`s it plus an optional pod2man man page; the
script needs only core modules — Module::Load, POSIX, Encode,
Digest::MD5, Term::ANSIColor — while Term::ReadKey is optional with a
built-in stty fallback).  OHOS ships a system perl at
/data/service/hnp/bin, so build() runs `perl -c` as the syntax gate and
the consumer test executes the packaged script for real.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

PERL = "/data/service/hnp/bin/perl"


class MypagerConan(ConanFile):
    name = "mypager"
    version = "0.6.3"
    description = ("mypager: lightweight terminal pager (less-like) with "
                   "UTF-8 support, MD5 jump positions and ANSI colours")
    license = "Artistic-2.0"
    homepage = "https://github.com/romuald/mypager"
    url = "https://github.com/romuald/mypager"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def configure(self):
        self.options.rm_safe("shared")
        self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # Upstream smoke gate: the script must compile under the system perl.
        # (Upstream Makefile has no test target; its `default` target merely
        # prints an install hint.)
        self.run(f'"{PERL}" -c mypager', cwd=src)
        # mypager has no --help switch: run argless it pages stdin until EOF,
        # which hangs a CI worker whose stdin never closes.  --installconf is
        # the one documented flag (writes ~/.mypager.conf, exit 0); HOME is
        # pointed at a fresh dir so no real config is touched and the
        # overwrite prompt (which reads stdin) cannot trigger.
        confhome = os.path.join(self.build_folder, "confhome")
        os.makedirs(confhome, exist_ok=True)
        self.run(f'HOME="{confhome}" "{PERL}" mypager --installconf', cwd=src)
        self.run(f'test -f "{confhome}/.mypager.conf"')

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "mypager", src=self.source_folder, dst=bindir, keep_path=False)
        os.chmod(os.path.join(bindir, "mypager"), 0o755)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
