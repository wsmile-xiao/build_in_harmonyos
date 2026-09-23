#!/usr/bin/env python3
"""Conan recipe - libgsasl-tools 2.2.4 (the GNU SASL `gsasl` program).

Upstream: https://ftp.gnu.org/gnu/gsasl/gsasl-2.2.4.tar.gz

This package ships only the upstream command line program:

    gsasl      client / server negotiation, --client-mechanisms,
               --server-mechanisms and --mkpasswd

The library itself (`libgsasl.a`, `gsasl.h`, `libgsasl.pc`) belongs to the
separate `libgsasl` package.  Upstream's `examples/` are `noinst_PROGRAMS`
(client, client-serverfirst, client-mech, smtp-server) so *nothing* else in
this tarball is installable - `src/Makefile.am` is literally

    bin_PROGRAMS = gsasl

which makes `gsasl` the whole tools surface.

The library and the program are produced by one and the same
`./configure && make`; the split only exists at the Makefile level
(`lib/src/Makefile.am` declares `lib_LTLIBRARIES = libgsasl.la` plus
`include_HEADERS`, `src/Makefile.am` declares `bin_PROGRAMS`).  A tools-only
package therefore still builds the whole tree and then installs exactly
`make -C src install-exec DESTDIR=...`, the same pattern ldns-tools uses with
`install-drill install-examples`.

Linked statically (R26): `--disable-shared --enable-static` makes the single
binary self contained, so this package never ships a `libgsasl.so` that could
collide with the `libgsasl` package - and, conversely, the binary can never end
up with an unsatisfied `DT_NEEDED libgsasl.so.0` after `lib/` is pruned.

Two upstream probes are explicitly disabled because they search the *system*
prefixes (`AC_LIB_HAVE_LINKFLAGS` looks at system dirs and LD_LIBRARY_PATH, not
at pkg-config): GnuTLS (`--without-gnutls`) and GNU libidn
(`--without-stringprep`).  Leaving them on can silently satisfy the probe from
`/usr/local`, which yields a non hermetic binary whose DT_NEEDED nobody ships.
GSS-API is not available on OHOS at all (`--disable-gssapi --disable-gs2`).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
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


class LibgsaslToolsConan(ConanFile):
    name = "libgsasl-tools"
    version = "2.2.4"
    description = "The gsasl command line client/server from GNU SASL"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/gsasl/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libgsasl-tools supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Static link: the tool then needs nothing but libc at runtime and this
        # package never ships a libgsasl that could collide with the library
        # package.
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        # No gettext catalogs in an application package.
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--disable-gtk-doc")
        # Both probes use AC_LIB_HAVE_LINKFLAGS, which searches the system
        # prefixes and LD_LIBRARY_PATH instead of pkg-config; on the OHOS worker
        # that can be satisfied by /usr/local and poison the link line.
        tc.configure_args.append("--without-gnutls")
        tc.configure_args.append("--without-stringprep")
        # No GSS-API implementation exists on OHOS.
        tc.configure_args.append("--disable-gssapi")
        tc.configure_args.append("--disable-gs2")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HarmonyOS: configure creates its scratch directory with
        # `umask 077 && mktemp -d ./confXXXXXX`, and HMDFS ignores chmod, so
        # config.status then dies with
        # "can't create ./confXXXXXX/subs1.awk: Permission denied".
        # Same fix as the ldns-tools / libdv-tools archives.
        configure_path = os.path.join(self.source_folder, "configure")
        replace_in_file(
            self,
            configure_path,
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
            'tmp="${TMPDIR:-/tmp}/conf$$" && (umask 000 && mkdir -p "$tmp") &&',
        )
        replace_in_file(
            self,
            configure_path,
            '  tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")',
            '  tmp=${TMPDIR:-/tmp}/conf$$-$RANDOM\n  (umask 000 && mkdir -p "$tmp")',
        )
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        # `src/` is the only directory with an installable program
        # (bin_PROGRAMS = gsasl); lib/, include/ and the pkg-config file belong
        # to the libgsasl package, and the po/ catalogs are disabled above.
        autotools.make(
            args=["-C", "src", f"DESTDIR={self.package_folder}"],
            target="install-exec",
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        # Defensive: only bin/ may survive in this package.
        for name in ("include", "lib", "share"):
            path = os.path.join(self.package_folder, name)
            if os.path.isdir(path):
                rmdir(self, path)
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
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