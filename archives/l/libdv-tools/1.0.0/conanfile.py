#!/usr/bin/env python3
"""Conan recipe - libdv-tools 1.0.0 (encodedv, dvconnect, dubdv).

Upstream: https://sourceforge.net/projects/libdv/  (libdv 1.0.0, 2005)

This package ships only the three command line programs that live in the
upstream `encodedv/` directory.  The DV codec library itself, its headers and
libdv.pc belong to the separate libdv package, so this recipe builds the
library statically into the tools and then trims the install tree down to
bin/ (+ the license).

Why it is not just "the library recipe with a smaller package()":

* encodedv/dubdv/dvconnect parse their command line with popt and the link
  line gets popt from `$(POPT_LIB)`, which configure.ac fills in with
  AC_CHECK_LIB(popt, poptGetContext).  When popt is missing configure only
  emits a warning - the tools are still built, but compiled without
  HAVE_LIBPOPT: the whole `#if HAVE_LIBPOPT` block (option table, --version,
  --help, usage) disappears, so `encodedv --version` prints nothing and exits
  0 and a bare `encodedv` walks off the end of argv and dies with SIGSEGV.
  This recipe therefore makes popt/1.16 a hard requirement, passes its
  -L/-I to configure itself (AutotoolsToolchain does not do that), and
  refuses to package anything unless config.h really defines HAVE_LIBPOPT.
* The shipped config.guess/config.sub are from 2005: they do not know
  `aarch64` at all, and OHOS's `uname -s` is `HarmonyOS`, which no branch in
  the 2005 case table matches.  Patches 0001/0002 therefore *add* the missing
  rules (10 + 29 lines) instead of replacing either script wholesale.  Note
  that this project builds with AM_MAINTAINER_MODE (default: disabled), so
  `configure` is *not* regenerated at build time - unlike libbs2b there is no
  autoreconf step and the patched helper scripts stay in place.
* libdv/dv.h includes <libdv/dv_types.h>, i.e. the parent of libdv/ has to be
  on the include path.  The upstream build only ever ran in-tree, where
  automake's DEFAULT_INCLUDES (-I. -I$(srcdir)) covers that by accident;
  building out of tree the way Conan does needs an explicit -I<source root>,
  which generate() adds.
* configure.ac enables X/GTK/Xvideo display support by default (playdv), which
  cannot work on HarmonyOS, and x86 inline assembly for the IDCT.
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
    rmdir,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibdvToolsConan(ConanFile):
    name = "libdv-tools"
    version = "1.0.0"
    description = ("Command line tools for libdv - encodedv, dubdv and "
                   "dvconnect")
    license = "LGPL-2.1-or-later"
    homepage = "https://sourceforge.net/projects/libdv/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # encodedv/dubdv/dvconnect need popt for their command line; without it
        # they still build but crash at startup (see the recipe docstring).
        self.requires("popt/1.16")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libdv-tools supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Tools-only: libdv is linked in statically, so the binaries never need
        # a libdv.so that this package would have to ship (and delete again).
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--enable-static")
        # HarmonyOS has no X11/GTK/Xv display, and the IDCT assembly is x86.
        tc.configure_args.append("--without-x")
        tc.configure_args.append("--disable-gtk")
        tc.configure_args.append("--disable-xv")
        tc.configure_args.append("--disable-asm")
        # libdv/dv.h does `#include <libdv/dv_types.h>`, so every translation
        # unit needs the *parent* of libdv/ on the include path.  In the
        # upstream in-tree build that is implicit (automake's DEFAULT_INCLUDES
        # is `-I. -I$(srcdir)`, and $(srcdir) == the top of the tree), but
        # Conan builds out of tree, so the compile line is only
        # `-I. -I<src>/libdv -I..` and the include resolves to nothing:
        #   libdv/dv.h:41:10: fatal error: 'libdv/dv_types.h' file not found
        # Add the source root explicitly instead of moving the build in-tree.
        tc.extra_cflags.append(f"-I{self.source_folder}")
        # configure.ac probes popt with AC_CHECK_LIB(popt, poptGetContext) and
        # the sources include <popt.h>; Conan's AutotoolsToolchain does not put
        # a dependency's -L/-I on the configure command line by itself, so add
        # them here.  Without them configure only *warns* ("checking for
        # poptGetContext in -lpopt... no"), the tools are still built, and
        # they then crash on startup - see _assert_popt_detected().
        popt = self.dependencies["popt"]
        tc.extra_cflags.append(f"-I{os.path.join(popt.package_folder, 'include')}")
        tc.extra_ldflags.append(f"-L{os.path.join(popt.package_folder, 'lib')}")
        tc.generate()

    def build(self):
        self._relax_configure_tempdir()
        autotools = Autotools(self)
        autotools.configure()
        self._assert_popt_detected()
        # -j1: the HMDFS jobserver fifo makes parallel make report
        # "jobserver mkfifo: Operation not permitted" (E074).
        autotools.make(args=["-j1"])

    def _relax_configure_tempdir(self):
        # configure creates its scratch directory with "umask 077 && mktemp -d
        # ./confXXXXXX"; HMDFS ignores chmod, so the directory is not writable
        # afterwards and config.status dies.  Redirect it to $TMPDIR.
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            return
        replace_in_file(
            self, configure,
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
            'tmp="${TMPDIR:-/tmp}/conf$$" && (umask 000 && mkdir -p "$tmp") &&',
            strict=False,
        )
        replace_in_file(
            self, configure,
            '  tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")',
            '  tmp=${TMPDIR:-/tmp}/conf$$-$RANDOM\n  (umask 000 && mkdir -p "$tmp")',
            strict=False,
        )

    def _assert_popt_detected(self):
        # AC_CHECK_LIB(popt, poptGetContext) only *warns* when popt is absent,
        # so the build would happily produce tools that segfault on startup.
        # A plain `"HAVE_LIBPOPT" in text` test does NOT work here: autoheader
        # writes the negative result as a comment, `/* #undef HAVE_LIBPOPT */`,
        # which contains the symbol name and makes the check pass anyway.
        for base in (self.build_folder, self.source_folder):
            config_h = os.path.join(base, "config.h")
            if os.path.isfile(config_h):
                with open(config_h, encoding="utf-8", errors="replace") as fh:
                    if "#define HAVE_LIBPOPT" not in fh.read():
                        raise ConanException(
                            "configure did not detect popt (no '#define "
                            "HAVE_LIBPOPT' in config.h): encodedv/dubdv/dvconnect "
                            "would be built without their command line parser -> "
                            "`encodedv --version` prints nothing and a bare "
                            "`encodedv` dies with SIGSEGV. Make sure popt/1.16 is "
                            "available and that its -L/-I reach configure (see "
                            "generate())."
                        )
                return

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        # Tools-only package: libdv.a, the public headers, libdv.pc and the man
        # pages belong to the libdv package - drop them so no file ever has two
        # owners.
        for name in ("include", "lib", "share"):
            path = os.path.join(self.package_folder, name)
            if os.path.isdir(path):
                rmdir(self, path)
        bindir = os.path.join(self.package_folder, "bin")
        for tool in ("encodedv", "dubdv", "dvconnect"):
            if not os.path.isfile(os.path.join(bindir, tool)):
                raise ConanException(f"{tool} was not installed")
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # HarmonyOS only loads ELF binaries that carry a valid .codesign
        # section; llvm-objcopy/binary-sign-tool ship in the OHOS SDK.
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        bindir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bindir):
            return
        for name in sorted(os.listdir(bindir)):
            path = os.path.join(bindir, name)
            if not os.path.isfile(path) or os.path.islink(path):
                continue
            if not self._is_elf(path):
                continue
            self.run(
                '{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                    oc=objcopy, f=path
                )
            )
            self.run(
                '{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                    sg=signer, f=path
                )
            )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = []
        self.cpp_info.libs = []