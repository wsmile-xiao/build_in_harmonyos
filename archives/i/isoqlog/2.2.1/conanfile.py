#!/usr/bin/env python3
"""Conan recipe for isoqlog 2.2.1 (HarmonyOS PC / OHOS aarch64).

Device note (E386 family, direvent/5.5 precedent): the OHOS Conan profile
exports SHELL/CONFIG_SHELL pointing at /data/service/hnp/bin/bash.  autoconf
re-executes configure through $CONFIG_SHELL, so on this runtime configure dies
with "cannot run /data/service/hnp/bin/bash ./config.sub".  configure/make/
install are therefore invoked through `env -u CONFIG_SHELL SHELL=/bin/sh`,
which keeps the full Conan toolchain environment but routes shell execution to
the working /bin/sh.

The upstream 2001-vintage config.sub (timestamp 2001-08-13) does not know the
linux-ohos triplet ("machine `aarch64-unknown-linux' not recognized") and the
matching config.guess cannot guess anything on HarmonyOS, so both triples are
passed explicitly as aarch64-unknown-linux-gnu (units/vo-aacenc/direvent
precedent).

patches/0001-isoqlog-Data.h.patch + 0002-isoqlog-Data.c.patch fix a 64-bit latent defect that
makes every non-empty run crash: Data.h declares the report sort table as
"struct SortDomain { int *allusers; }" (Data.h:110) and Data.c fills it with
"allusers[n] = (int)usr", i.e. it moves user* through a 32-bit int.  Heap
addresses on this device sit in the 0x63_xxxxxxxx range -- measured twice via
/proc/self/maps ([anon:native_heap:jemalloc] at 6377001000-6377201000 and
6386a01000-6386c01000; ASLR changes the exact value, it never brings it below
2^32), so the stored value is truncated and the sign-extended read back in
Html.c dereferences an unmapped address -> SIGSEGV (rc 139) as soon as the log
yields one record, while an empty log still exits 0.  Neither the compiler nor
the linker warns because the narrowing is written as an explicit cast.  The
patch only retypes the container (and every int tmp in the eight sort*()
helpers) to the real pointer type; no algorithm or output changes.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, export_conandata_patches, get,
                               replace_in_file)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

SH = "env -u CONFIG_SHELL SHELL=/bin/sh"
CONFIGURE_ARGS = (
    "--prefix=/"
    " '--bindir=${prefix}/bin'"
    " '--sbindir=${prefix}/bin'"
    " '--libdir=${prefix}/lib'"
    " '--includedir=${prefix}/include'"
    " '--oldincludedir=${prefix}/include'"
    " --build=aarch64-unknown-linux-gnu"
    " --host=aarch64-unknown-linux-gnu"
)


class IsoqlogConan(ConanFile):
    name = "isoqlog"
    version = "2.2.1"
    description = ("isoqlog is a traffic analysis program which provides "
                   "interesting statistics from logs (sendmail, postfix, qmail, "
                   "vpopmail, imap, http, firewall)")
    license = "BSD-3-Clause"
    homepage = "https://packages.ubuntu.com/noble/isoqlog"
    topics = ("log-analyzer", "statistics", "html-report")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("isoqlog is supported only on Linux and OHOS")
        if str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration("isoqlog is packaged for the aarch64 target")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # configure is invoked directly in build() with CONFIGURE_ARGS (the single
        # source of the cross-triple flags), so nothing is added to
        # tc.configure_args here; only the compiler flags below flow through
        # conanbuild.sh.
        # 经验汇总 §12.21 / §12.49(f): clang 15 defaults to -fno-common, and this
        # 2003-vintage tree puts a *tentative definition* in a header:
        #   isoqlog/Dir.h:9   int cur_year, cur_month, cur_day, cur_hour, cur_min, cur_sec;
        # Dir.h is included by five translation units (Dir.c, Html.c, Store.c,
        # loadconfig.c, main.c), so every object file emits the same .bss symbols
        # and the link fails with "ld.lld: error: duplicate symbol: cur_month"
        # (Store.o vs Dir.o, create-05.log).  -fcommon restores the classic
        # common-symbol merging without patching upstream sources
        # (alex4/arpalert precedent).
        tc.extra_cflags.append("-fcommon")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder

        # E011/E114 (HMDFS): this autoconf 2.53 config.status creates its temp
        # dir with `(umask 077 && mktemp -d -q "$TMPDIR/csXXXXXX")`.  On hmdfs
        # the 077 mode inherits the parent's setgid bit as an uppercase S and
        # the directory stays unwritable, so config.status never emits any
        # Makefile -- device evidence (2026-09-24, create-04.log):
        #   rm: /storage/Users/currentUser/csoBGkDg/in: Permission denied
        #   ./config.status[1006]: can't open Makefile: No such file or directory
        #   make: *** No targets specified and no makefile found.
        # Relax the wrap to 002 (direvent/5.5 precedent).  replace_in_file has no
        # count argument and rewrites *every* match, and the 2.53 configure ships
        # exactly two "umask 077" sites (pristine configure:4386 mktemp branch and
        # :4391 mkdir fallback -- `grep -n umask configure` returns nothing else),
        # so one call covers both.
        replace_in_file(self, os.path.join(src, "configure"), "umask 077", "umask 002")
        # The device exports TMPDIR=$HOME and /tmp is read-only, so config.status
        # would drop its csXXXXXX scratch dir in the home root (AGENTS §4 forbids
        # new stray files there).  Pin it inline instead of mutating os.environ so
        # the override cannot leak into other packages or steps of this build.
        env = f'{SH} TMPDIR="{self.build_folder}"'
        self.run(f'cd "{src}" && {env} sh ./configure {CONFIGURE_ARGS}')
        self.run(f'cd "{src}" && {env} make -j1')
        # Upstream distributes no automated test entry point: there is no
        # "check" target in any Makefile.am/Makefile.in (N_static = 0), so
        # `make check` is not invoked.  Behaviour is covered by the
        # test_package consumer test instead.

    def package(self):
        src = self.source_folder
        self.run(f'cd "{src}" && {SH} make install DESTDIR="{self.package_folder}/"')

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
