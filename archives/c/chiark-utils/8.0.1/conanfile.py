#!/usr/bin/env python3
"""Conan recipe — chiark-utils 8.0.1 (bare-Makefile multi-tool package).

Upstream has NO configure: cprogs/Makefile is driven directly with make,
compiler/link flags injected via the upstream CMDLINE_CPPFLAGS / CMDLINE_LDFLAGS
hooks (settings.make). Dependency paths come from each Conan dependency's
cpp_info (R49: no shared system prefix injection).

Upstream conditionally drops acctdump when sys/acct.h is missing; the same
upstream Makefile mechanism keeps the build self-adapting on OHOS.

`really` is installed SUID upstream (-m 4774 -o root); Conan packaging copies
it as a normal binary — SUID bits are meaningless on OHOS and are not set.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout
import os


class ChiarkutilsConan(ConanFile):
    name = "chiark-utils"
    version = "8.0.1"
    description = "Ian Jackson's chiark system utilities (backup, locking, X11 monitors, nettle hash tools)"
    license = "GPL-3.0-or-later"
    homepage = "https://www.chiark.greenend.org.uk/ucgi/~ian/git/chiark-utils.git"
    url = "https://deb.debian.org/debian/pool/main/c/chiark-utils/chiark-utils_8.0.1.tar.xz"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    # no options: pure CLI tool suite, no library surface

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("nettle/3.10.2.1")
        self.requires("gmp/6.3.0")
        self.requires("libx11/1.8.13")
        self.requires("libuv/1.52.1")
        # xorgproto (X11/X.h, keysym defs) is pulled transitively by libx11 but
        # flagged visible=False in the graph -> its include dir never reaches
        # our bare-Makefile flag injection. Declare it directly (E221-family).
        self.requires("xorgproto/2025.1", force=True)
        # NOTE: xduplic-copier is excluded because it is the only program
        # needing libxmu/1.3.1, which is merged in main but NOT yet published
        # to the registry (R36). Re-add both in 8.0.1.1 once libxmu is released.

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dep_flags(self):
        incs, libs = [], []
        for _, dep in self.dependencies.items():
            for d in dep.cpp_info.includedirs:
                incs.append("-I" + d)
            for d in dep.cpp_info.libdirs:
                libs.append("-L" + d)
        # dedupe, keep order
        incs = list(dict.fromkeys(incs))
        libs = list(dict.fromkeys(libs))
        return " ".join(incs), " ".join(libs)

    def generate(self):
        # R33: compiler comes from Conan conf in build(); no env script needed.
        # (Saving a custom env script as "conanbuild" collides with Conan's
        #  own aggregated launcher and creates a self-sourcing script -> SIGSEGV)
        pass

    def build(self):
        apply_conandata_patches(self)
        comp = self.conf.get("tools.build:compiler_executables", check_type=dict) or {}
        cc = comp.get("c", "clang")
        incs, libs = self._dep_flags()
        make_vars = (
            'CC="%s" '
            "CMDLINE_CPPFLAGS='%s' "
            # OHOS <libintl.h> is a stub that does not declare gettext().
            # Identity-map gettext so upstream `#define _(x) gettext(x)`
            # keeps compiling (English messages, same as musl default).
            # nested quotes: outer quotes are stripped by the shell invoking
            # make, the inner singles must survive into the make recipe line
            "CMDLINE_CFLAGS=\"'-Dgettext(x)=x'\" "
            "CMDLINE_LDFLAGS='%s' "
            # command-line PROGRAMS override: drop xduplic-copier (the only
            # consumer of libxmu, unpublished on the registry, R36). acctdump
            # is included explicitly because a command-line PROGRAMS assignment
            # suppresses the Makefile's conditional `PROGRAMS+=acctdump`
            'PROGRAMS="readbuffer writebuffer with-lock-ex xbatmon-simple '
            'summer watershed rcopy-repeatedly prefork-interp '
            'cgi-fcgi-interp acctdump" '
            % (cc, incs, libs)
        )
        # upstream make check: none exists for cprogs; the tool binaries
        # themselves are smoke-tested in test_package (R51 declared in MANIFEST)
        srcdir = os.path.join(self.source_folder, "cprogs")
        self.run('cd "%s" && make %s -j1' % (srcdir, make_vars))

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        sbindir = os.path.join(self.package_folder, "sbin")
        mandir1 = os.path.join(self.package_folder, "share", "man", "man1")
        mandir8 = os.path.join(self.package_folder, "share", "man", "man8")
        docdir = os.path.join(self.package_folder, "share", "doc", "chiark-utils")
        for d in (bindir, sbindir, mandir1, mandir8, docdir):
            os.makedirs(d, exist_ok=True)

        # basic_layout: build() ran make inside source_folder/cprogs (no
        # separate build dir was created by the bare Makefile); build_folder
        # only holds conan-generated env/metadata under build-release/
        src = os.path.join(self.source_folder, "cprogs")
        programs = ["readbuffer", "writebuffer", "with-lock-ex", "xbatmon-simple",
                    "summer", "watershed", "rcopy-repeatedly",
                    "prefork-interp", "cgi-fcgi-interp", "acctdump"]
        daemons = ["trivsoundd"]
        sbin_tools = ["really"]
        for p in programs:
            copy(self, p, src=src, dst=bindir)
        for p in daemons + sbin_tools:
            copy(self, p, src=src, dst=sbindir)
        copy(self, "*.1", src=src, dst=mandir1)
        copy(self, "*.8", src=src, dst=mandir8)
        copy(self, "*.txt", src=src, dst=docdir)
        # LICENSE
        copy(self, "COPYING", src=self.source_folder, dst=docdir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
