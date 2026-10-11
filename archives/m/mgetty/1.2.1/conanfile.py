#!/usr/bin/env python3
"""Conan recipe for mgetty 1.2.1 (mgetty+sendfax) — upstream Makefile build.

Upstream: http://mgetty.greenie.net/ (Gert Doering), tarball
http://mgetty.greenie.net/source/1.2/mgetty-1.2.1.tar.gz (official site is
plain-HTTP/FTP only; the https front is not served). sha256 verified equal to
the official ftp:// copy.

mgetty is a smart getty (dial-in login) with the sendfax/faxspool/faxrunqd
fax suite and the G3 fax image tools (pbm2g3/g32pbm/g3cat/sff2g3). It is a
plain-Makefile project: upstream asks the builder to copy policy.h-dist to
policy.h, adjust CC / CFLAGS / the *DIR variables in the Makefile, then run
`make` / `make test` / `make install`. There is no configure script.

OHOS adaptation:
- R33: the C compiler comes from the Conan profile
  (tools.build:compiler_executables) through AutotoolsToolchain; CFLAGS/
  LDFLAGS are read from the generated toolchain environment, never from bare
  shell variables. The makefile's hard-coded CFLAGS are overridden on the
  make command line (GNU make: command-line variables win).
- LP64: mgetty's config.h picks `typedef int p_int` unless PTR_IS_LONG is
  defined; on the 64-bit (LP64) OHOS target the pointer-sized integer must be
  `long`, so -DPTR_IS_LONG is added (this is upstream's own knob).
- LIBS is emptied: the upstream default is `-lutil` (Linux), which does not
  exist on OHOS/musl (openpty/logwtmp live in libc there).
- patches/: logfile.c used sys_nerr/sys_errlist, which musl does not provide;
  the lookup is replaced by the standard strerror() (portable, no platform
  macro).

Upstream tests (`make test`, R51) run the g3/ image-tool suite and the t/
C/shell tests; they are executed in build() and their output is recorded in
notes.md.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import build_jobs
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class MgettyConan(ConanFile):
    name = "mgetty"
    version = "1.2.1"
    description = ("mgetty+sendfax: smart getty with class-2 fax/voice support "
                   "(sendfax, faxspool, faxrunqd, G3 tools)")
    license = "GPL-2.0-or-later"
    homepage = "http://mgetty.greenie.net/"
    url = "http://mgetty.greenie.net/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # mgetty has no out-of-tree build: build in the source folder
        # (abduco/plain-Makefile precedent).
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: compiler/flags from the Conan toolchain, not bare shell vars.
        tc = AutotoolsToolchain(self)
        env = tc.environment().vars(self)
        self._cc = env.get("CC", "clang")
        self._cflags = env.get("CFLAGS", "") or "-O2"
        self._ldflags = env.get("LDFLAGS", "")
        tc.generate()

    def _make(self, target):
        # GNU make: command-line variable assignments override the Makefile's
        # hard-coded CFLAGS/CC. Values are quoted so multi-word flags survive.
        jobs = build_jobs(self) or 1
        cmd = ('make -j%d %s CC="%s" CFLAGS="%s" LDFLAGS="%s" LIBS='
               % (jobs, target, self._cc, self._cflags, self._ldflags))
        self.output.info("R51/build: %s" % cmd)
        self.run(cmd)

    def build(self):
        apply_conandata_patches(self)
        # Upstream: "copy policy.h-dist to policy.h" before building.
        shutil.copyfile(os.path.join(self.source_folder, "policy.h-dist"),
                        os.path.join(self.source_folder, "policy.h"))
        # -DPTR_IS_LONG: config.h selects `long p_int` only when this is set;
        # required on the LP64 (aarch64) target.
        self._cflags = " ".join(filter(None, [self._cflags, "-DPTR_IS_LONG"]))
        # bin-all = mgetty sendfax newslock sedscript + g3/tools/fax/callback
        # subdirs (the `all` target additionally formats man pages, which needs
        # nroff/groff and is not required for packaging). The three default
        # config files are generated from *.cfg.in by ./sedscript (install.bin
        # prerequisites), so build them explicitly.
        self._make("bin-all login.config mgetty.config sendfax.config")
        # Upstream test suite (g3/ image tools + t/ unit/script tests, R51).
        self._make("test")

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        for exe in ("mgetty", "sendfax", "newslock"):
            copy(self, exe, src=self.build_folder, dst=bin_dir, keep_path=False)
        for exe in ("g3cat", "g32pbm", "pbm2g3", "sff2g3"):
            copy(self, exe, src=os.path.join(self.build_folder, "g3"),
                 dst=bin_dir, keep_path=False)
        for exe in ("faxspool", "faxrunq", "faxq", "faxrm", "faxrunqd",
                    "faxq-helper"):
            copy(self, exe, src=os.path.join(self.build_folder, "fax"),
                 dst=bin_dir, keep_path=False)

        conf_dir = os.path.join(self.package_folder, "etc", "mgetty+sendfax")
        for cfg in ("login.config", "mgetty.config", "sendfax.config",
                    "dialin.config", "faxrunq.config"):
            copy(self, cfg, src=self.build_folder, dst=conf_dir, keep_path=False)
        for cfg in ("faxheader", "faxspool.rules"):
            copy(self, cfg, src=os.path.join(self.build_folder, "fax"),
                 dst=conf_dir, keep_path=False)

        lib_dir = os.path.join(self.package_folder, "lib", "mgetty+sendfax")
        for data in ("cour25.pbm", "cour25n.pbm"):
            copy(self, data, src=os.path.join(self.build_folder, "fax"),
                 dst=lib_dir, keep_path=False)

        # The fax front-ends (faxspool/faxrunq/faxq/faxrm) are shell/perl
        # scripts generated by sedscript and are not executable in the build
        # tree; upstream `make install` marks them 755. Do the same here
        # (HMDFS normalises the mode to 770 — E046, still executable).
        for entry in os.listdir(bin_dir):
            os.chmod(os.path.join(bin_dir, entry), 0o755)

        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
