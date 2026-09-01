#!/usr/bin/env python3
"""Conan recipe for ldns 1.9.0 — Autotools (configure + make).

ldns is a DNS library supporting DNSSEC operations.
Depends on OpenSSL for crypto functionality.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LdnsConan(ConanFile):
    name = "ldns"
    version = "1.9.0"
    description = "ldns is a DNS library with support for DNSSEC operations"
    license = "BSD-3-Clause"
    homepage = "https://www.nlnetlabs.nl/projects/ldns/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_examples": [True, False],
        "with_drill": [True, False],
    }
    default_options = {
        "shared": False,
        "with_examples": True,
        "with_drill": True,
        # R26: OpenSSL is a system-name library, default static
        "openssl/*:shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")

        # Project-specific configure args
        tc.configure_args.append("--with-examples" if self.options.with_examples else "--without-examples")
        tc.configure_args.append("--with-drill" if self.options.with_drill else "--without-drill")

        # Point to OpenSSL from Conan dependencies
        openssl = self.dependencies["openssl"]
        openssl_root = openssl.package_folder
        tc.configure_args.append(f"--with-ssl={openssl_root}")

        tc.generate()

    def build(self):
        # Apply patches: config.guess + config.sub HarmonyOS support
        apply_conandata_patches(self)

        # Fix config.status temp directory creation on HarmonyOS
        # mktemp -d with umask 077 creates directories that HarmonyOS SELinux
        # denies file creation within. Use mkdir -p with umask 000 instead.
        configure_path = os.path.join(self.source_folder, "configure")
        replace_in_file(
            self, configure_path,
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
            'tmp="${TMPDIR:-/tmp}/conf$$" && (umask 000 && mkdir -p "$tmp") &&',
        )
        replace_in_file(
            self, configure_path,
            '  tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")',
            '  tmp=${TMPDIR:-/tmp}/conf$$-$RANDOM\n  (umask 000 && mkdir -p "$tmp")',
        )

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        # Run specific install targets, skip install-manpages (470+ man3 pages cause timeout)
        autotools = Autotools(self)
        autotools.make(
            target="install-h install-lib install-pc install-config install-drill install-examples",
            args=[f"DESTDIR={self.package_folder}"],
        )

    def package_info(self):
        self.cpp_info.libs = ["ldns"]
        self.cpp_info.requires = ["openssl::openssl"]
