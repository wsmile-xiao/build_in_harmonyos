#!/usr/bin/env python3
"""Conan recipe - ldns-tools 1.9.2 (DNS / DNSSEC command line tools).

Upstream: https://www.nlnetlabs.nl/downloads/ldns/ldns-1.9.2.tar.gz

This package ships only the upstream command line programs:

    drill                      dig style DNS debugger
    ldns-read-zone, ldns-keygen, ldns-key2ds, ldns-signzone,
    ldns-verify-zone, ldns-notify, ldns-walk, ldns-zcat, ldns-zsplit,
    ldns-gen-zone, ldns-test-edns, ldns-version, ldns-zone-digest, ...

The library itself belongs to the separate `ldns` package.

Upstream builds the library and the programs from one and the same
`./configure && make`; --with-drill / --with-examples only decide whether the
extra programs get compiled, and the real split only exists at the Makefile
install-target level.  A tools-only package therefore still builds the whole
tree and then installs exactly `install-drill install-examples`.  The aggregate
`install` target must NOT be used here: it also pulls in `install-manpages`,
whose 470+ ldns_*.3 pages are irrelevant for a tools package and time the OHOS
build out (the ldns archive hit the same wall).

OpenSSL is needed by drill and by the signing/verification examples, and is
linked statically (R26).
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


class LdnsToolsConan(ConanFile):
    name = "ldns-tools"
    version = "1.9.2"
    description = "Command line tools for ldns - DNS and DNSSEC utilities"
    license = "BSD-3-Clause"
    homepage = "https://www.nlnetlabs.nl/projects/ldns/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ldns-tools supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Static link: the tools then need nothing but libc at runtime and
        # this package never ships a libldns that could collide with the
        # ldns package.
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        # The two switches that actually produce the programs.
        tc.configure_args.append("--with-drill")
        tc.configure_args.append("--with-examples")
        # No SWIG / python bindings: they are not command line tools.
        tc.configure_args.append("--without-pyldns")
        openssl_root = self.dependencies["openssl"].package_folder
        tc.configure_args.append(f"--with-ssl={openssl_root}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HarmonyOS: config.status creates its scratch directory with
        # `umask 077 && mktemp -d`, and HMDFS denies file creation inside a
        # 0700-sticky scratch dir, so config.status dies with
        # "can't create ./confXXXXXX/subs1.awk: Permission denied".
        # Same fix as the ldns archive.
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
        # Tools-only install targets: drill + the examples programs and their
        # man1 pages.  install-lib / install-h / install-pc / install-manpages
        # belong to the ldns package.
        autotools.make(
            target="install-drill install-examples",
            args=[f"DESTDIR={self.package_folder}"],
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        # Defensive: if a future Makefile ever grows a shared prerequisite,
        # make sure only bin/ survives in this package.
        for name in ("include", "lib"):
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