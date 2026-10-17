#!/usr/bin/env python3
"""Conan recipe — cfingerd 1.4.3 (custom Perl Configure + makefile).

Build system: custom Perl Configure script (metaconfig-style, 1999),
NOT autotools. Configure generates src/config.h + Makefile.cfg non-interactively
via `-c foo=bar` args, then plain make builds two binaries.

Platform notes (OHOS adaptation):
  - Perl 5.42 does not search cwd in @INC → export PERL5LIB=<src_dir>
  - uname returns HARMONYOS which falls to the generic branch (gmake);
    force os_type=LINUX so the make/cflags defaults apply
  - no `cc` alias on OHOS → pass CC=clang explicitly (R33: from Conan conf)
  - upstream Install script is interactive → install by copy() instead
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CfingerdConan(ConanFile):
    name = "cfingerd"
    version = "1.4.3"
    description = "Configurable and secure finger daemon (cfingerd)"
    license = "GPL-1.0-or-later"
    homepage = "https://www.infodrom.org/projects/cfingerd/"
    url = ""  # CI fills this

    package_type = "application"
    build_policy = "missing"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass  # plain makefile build, no toolchain file needed

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler executables come from Conan conf, never bare env vars.
        # The ohos-aarch64 profile sets tools.build:compiler_executables as a
        # JSON dict ({"c": ..., "cpp": ...}); read the whole key, not the
        # dotted sub-key (which Conan 2.29 rejects as non-existent conf).
        comp = self.conf.get("tools.build:compiler_executables", {}, check_type=dict)
        cc = comp.get("c", "clang")

        # Step 1: non-interactive Configure (custom Perl script).
        #   Perl 5.42 @INC does not include cwd, and conan's env= injection did
        #   not reliably propagate PERL5LIB to the child perl process, so pass
        #   the lib dir via `perl -I` directly (most robust on OHOS workers).
        #   os_type=LINUX: uname returns HARMONYOS on OHOS, the generic
        #   branch defaults to gmake which does not exist on the device.
        prefix = os.path.join(self.build_folder, "prefix")
        conf_cmd = (
            f"perl -I{self.source_folder} ./Configure"
            f" -c os_type=LINUX"
            f" -c make=make"
            f" -c cflags=-O2 -Wall"
            f" -c ldflags="
            f" -c config={prefix}/etc/cfingerd.conf"
            f" -c mandir={prefix}/share/man"
            f" -c nobody_uid=65534"
            f" -c nobody_gid=65534"
            f" -c mailspool=/var/spool/mail"
            f" -c lastlog=/var/log/lastlog"
        )
        self.run(conf_cmd, cwd=self.source_folder)

        # Step 2: build both binaries (R9: -j1).
        self.run(f"make all CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        # Upstream `make install` calls interactive Install script + chown
        # binaries to root — unusable in the OHOS sandbox. Install by copy().
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "cfingerd", os.path.join(self.source_folder, "src"), bindir)
        copy(self, "userlist", os.path.join(self.source_folder, "userlist"), bindir)
        copy(self, "cfingerd.conf", self.source_folder,
             os.path.join(self.package_folder, "res"))
        copy(self, "*.8", os.path.join(self.source_folder, "docs"),
             os.path.join(self.package_folder, "res", "man8"), keep_path=False)
        copy(self, "*.5", os.path.join(self.source_folder, "docs"),
             os.path.join(self.package_folder, "res", "man5"), keep_path=False)
        copy(self, "*.1", os.path.join(self.source_folder, "userlist"),
             os.path.join(self.package_folder, "res", "man1"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
