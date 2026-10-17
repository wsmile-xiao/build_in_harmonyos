#!/usr/bin/env python3
"""Conan recipe — ssmtp 2.64 (Autotools, autoconf 2.13 era).

Send-only sendmail emulator. Builds the ssmtp CLI tool with SSL/TLS support
(statically linked openssl), MD5 auth, IPv6 and logging enabled by default.
"""
import os
import re

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

class SsmtpConan(ConanFile):
    name = "ssmtp"
    version = "2.64"
    description = "Send-only sendmail emulator for machines which pick up mail from a centralized mailhub"
    license = "GPL-2.0-or-later"
    homepage = "https://packages.debian.org/source/ssmtp"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    options = {
        "with_ssl": [True, False],
        "with_md5auth": [True, False],
        "with_inet6": [True, False],
        "with_logfile": [True, False],
    }
    default_options = {
        "with_ssl": True,
        "with_md5auth": True,
        "with_inet6": True,
        "with_logfile": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        self.folders.build = self.folders.source

    def requirements(self):
        if self.options.with_ssl:
            self.requires("openssl/1.1.1w")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.with_ssl:
            tc.configure_args.append("--enable-ssl")
            # The autoconf 2.13 configure has no SSL detection at all:
            # --enable-ssl only appends "-lssl" to LIBS and defines HAVE_SSL.
            # The Makefile link line is "$(CC) -o ssmtp $(OBJS) @LIBS@ $(CFLAGS)"
            # (no LDFLAGS), so -L search paths and -lcrypto (needed by
            # SSL_load_error_strings) must travel inside LIBS. Configure
            # appends its own -lssl after the inherited LIBS, keeping the
            # correct static-link order (ssl before crypto).
            info = self.dependencies["openssl"].cpp_info.aggregated_components()
            ld_paths = " ".join(f"-L{d}" for d in info.libdirs)
            libs = " ".join(f"-l{l}" for l in info.libs)
            ssl_env = Environment()
            ssl_env.append("LIBS", f"{ld_paths} {libs}")
            ssl_env.vars(self, "build").save_script("conanssmtpssl")
        if self.options.with_md5auth:
            tc.configure_args.append("--enable-md5auth")
        if self.options.with_inet6:
            tc.configure_args.append("--enable-inet6")
        if self.options.with_logfile:
            tc.configure_args.append("--enable-logfile")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Cache hints for the old autoconf 2.13 tests. The "-g" test honors
        # these env cache vars; the compiler-works test has no cache check
        # but passes with the conan-provided toolchain environment.
        os.environ["ac_cv_prog_cc_works"] = "yes"
        os.environ["ac_cv_prog_cc_g"] = "yes"
        os.environ["ac_cv_prog_cc_cross"] = "no"
        autotools = Autotools(self)
        autotools.configure()
        # Old autoconf 2.13 Makefile has DEFS embedded in CFLAGS;
        # cannot override CFLAGS (loses DEFS) so patch the Makefile.
        # CPPFLAGS from the environment is NOT captured into the Makefile,
        # so the openssl include path must be appended here as well.
        makefile = os.path.join(self.build_folder, "Makefile")
        wflags = (
            " -Wno-int-conversion"
            " -Wno-void-pointer-to-int-cast"
            " -Wno-pointer-sign"
            " -Wno-array-bounds"
        )
        if self.options.with_ssl:
            info = self.dependencies["openssl"].cpp_info.aggregated_components()
            wflags += "".join(f" -I{d}" for d in info.includedirs)
        if os.path.exists(makefile):
            content = open(makefile).read()
            content = re.sub(
                r'^(CFLAGS\s*=.*)$',
                r'\1' + wflags,
                content,
                flags=re.MULTILINE
            )
            open(makefile, 'w').write(content)
        autotools.make(args=["-j1"])

    def package(self):
        bindir = os.path.join(self.package_folder, "sbin")
        mandir = os.path.join(self.package_folder, "share", "man", "man8")
        confdir = os.path.join(self.package_folder, "etc", "ssmtp")
        copy(self, "ssmtp", src=self.build_folder, dst=bindir, keep_path=False)
        copy(self, "ssmtp.8", src=self.source_folder, dst=mandir, keep_path=False)
        copy(self, "revaliases", src=self.source_folder, dst=confdir, keep_path=False)
        os.makedirs(confdir, exist_ok=True)
        with open(os.path.join(confdir, "ssmtp.conf"), "w") as f:
            f.write("# ssmtp configuration\nmailhub=mail\n")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["sbin"]
