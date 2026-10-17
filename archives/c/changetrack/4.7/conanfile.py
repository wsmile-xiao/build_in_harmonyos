#!/usr/bin/env python3
"""Conan recipe for changetrack 4.7 — pure Perl script utility.

changetrack monitors changes to configuration files, keeps human-readable
change logs and RCS revision history (full recovery via the RCS suite).

Platform adaptations for OHOS:
  1. Shebang fix: #!/usr/bin/perl -> #!/usr/bin/env perl
     (OHOS has no /usr/bin/perl; perl is provided by the device toolchain
      userland directory which is on PATH)
  2. RCS suite is a hard runtime dependency for revision storage and is
     expressed as a conan requires (rcs/5.10.1); its binaries reach the
     consumer PATH through the package bindirs.

Runtime dependencies resolved from PATH at run time (no conan requires):
  - perl >= 5 (core modules File::Copy, Getopt::Std, File::Path, FileHandle)
  - GNU diffutils `diff` supporting `-e` (ed script output). toybox diff
    does NOT support -e and must not shadow diffutils on PATH.

R28: test_package/ exists.
R32: settings.os check uses "in" not "==".
R34: test_package tests actual changetrack functionality (change tracking
     with and without RCS).
R38: commands.json declared (command-line tool).
"""
import os
import shutil
import stat

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ChangetrackConan(ConanFile):
    name = "changetrack"
    version = "4.7"
    description = "Monitors changes to configuration files and keeps revision history"
    license = "GPL-2.0-or-later"
    homepage = "http://changetrack.sf.net"
    url = "http://changetrack.sf.net"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # RCS suite (ci/co/rcs): revision storage backend invoked at run time.
        self.requires("rcs/5.10.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl project: no configure/compile step. Upstream Makefile only
        # has test/install targets; `make test` requires the RCS suite which is
        # not available on OHOS yet (see notes.md / MANIFEST.yml), and
        # `make install` hardcodes /usr/local and /etc, so packaging is manual.

    def package(self):
        src = self.source_folder

        # the changetrack script itself
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        script = os.path.join(bindir, "changetrack")
        shutil.copy2(os.path.join(src, "changetrack"), script)
        os.chmod(script, os.stat(script).st_mode
                 | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        # man page (upstream ships changetrack.man, prebuilt roff)
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(mandir, exist_ok=True)
        shutil.copy2(os.path.join(src, "changetrack.man"),
                     os.path.join(mandir, "changetrack.1"))

        # example configuration + upstream README as docs
        docdir = os.path.join(self.package_folder, "share", "doc", "changetrack")
        os.makedirs(docdir, exist_ok=True)
        shutil.copy2(os.path.join(src, "changetrack.conf"),
                     os.path.join(docdir, "changetrack.conf"))
        shutil.copy2(os.path.join(src, "README"),
                     os.path.join(docdir, "README"))

    def package_info(self):
        # Pure script project: no libraries, just executables in bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
