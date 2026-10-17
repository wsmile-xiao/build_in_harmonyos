#!/usr/bin/env python3
"""Conan recipe for otpw 1.5 (OTPW one-time password package, CLI part only).

Upstream is a bare Makefile (M18 family: `CC=gcc` is a plain assignment, so
only a command-line override wins; `install:` bakes Debian PAM paths and uses
rsync, so package() copies the artifact itself).

Scope decision (platform): musl/OHOS has no PAM ecosystem, and `pam_otpw.so`
links `-lcrypt -lpam -lpam_misc` plus PAM headers that do not exist here.  The
recipe therefore builds the upstream CLI tool `otpw-gen` only, via
`make TARGETS=otpw-gen` (command-line override of the Makefile's TARGETS
variable — zero patches).  demologin is a demo client and is likewise not
part of the delivered package.

Tested upstream behaviour this recipe relies on (see notes.md):
  * `otpw-gen -f <hashfile>` skips the /etc/passwd lookup entirely, so the
    full password-list generation path is executable on hosts whose uid has
    no passwd entry;
  * the prefix password is read from stdin (two identical lines);
  * `-r` prints a random password suggestion without touching any database.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get, copy
from conan.tools.layout import basic_layout


class OtpwConan(ConanFile):
    name = "otpw"
    version = "1.5"
    description = ("OTPW one-time password list generator (otpw-gen CLI); "
                   "PAM module excluded, see package_info/notes")
    license = "GPL-2.0-or-later"
    homepage = "https://www.cl.cam.ac.uk/~mgk25/otpw.html"
    url = "https://www.cl.cam.ac.uk/~mgk25/otpw.html"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # No patches: TARGETS is overridden on the make command line instead;
        # conandata.yml declares an empty patch set.
        pass


    def layout(self):
        basic_layout(self)
        # Bare Makefile with no VPATH: objects and the binary land next to
        # the sources, so the build tree *is* the source tree (ttygif 同型).
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)  # no-op: conandata declares an empty patch set
        # R33: compiler from Conan conf, never a bare ${CC}.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or "cc"
        # R9: -j1.  CFLAGS is a plain `=` assignment and is left untouched so
        # upstream's -O -W -Wall -fPIC defaults survive.
        self.run('make -j1 TARGETS=otpw-gen CC="%s"' % cc)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        licdir = os.path.join(self.package_folder, "licenses")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(licdir, exist_ok=True)
        copy(self, "otpw-gen", src=self.source_folder, dst=bindir,
             keep_path=False)
        copy(self, "README", src=self.source_folder, dst=licdir,
             keep_path=False)
        copy(self, "otpw.html", src=self.source_folder, dst=licdir,
             keep_path=False)
        exe = os.path.join(bindir, "otpw-gen")
        if not os.path.isfile(exe):
            raise ConanException("package(): missing build artifact %s" % exe)
        os.chmod(exe, 0o755)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
