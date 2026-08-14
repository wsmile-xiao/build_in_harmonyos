#!/usr/bin/env python3
"""Conan recipe for gsoap 2.8.142 — Autotools build system.

gSOAP is a SOAP/XML web services toolkit for C and C++.
Build with OpenSSL support (SSL enabled, no trimming).

OHOS adaptation:
- Patches fix config.guess/sub for OHOS platform detection
- Patches fix configure/depcomp/install-sh/mkinstalldirs for HMDFS
- Patches force poll() instead of select() to avoid __fd_chk dependency
- FORTIFY_SOURCE disabled (musl incompatibility)
- os.chmod fixes execute permissions lost during zip extraction
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout


class GsoapConan(ConanFile):
    name = "gsoap"
    version = "2.8.142"
    description = "SOAP/XML web services toolkit for C and C++"
    license = "GPLv2"
    homepage = "https://www.genivia.com"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/1.1.1w")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # FORTIFY_SOURCE workaround for OHOS musl
        tc.cflags.append("-U_FORTIFY_SOURCE")
        tc.cflags.append("-D_FORTIFY_SOURCE=0")
        tc.cxxflags.append("-U_FORTIFY_SOURCE")
        tc.cxxflags.append("-D_FORTIFY_SOURCE=0")
        tc.generate()
        # Generate dependency env vars and pkg-config for OpenSSL
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix timestamps to prevent make from trying to regenerate
        # Makefile.in/configure with automake (not available on OHOS)
        # Touch all .in and .am files plus configure/aclocal.m4 to current time
        for root, dirs, files in os.walk(self.source_folder):
            for f in files:
                if f.endswith(".in") or f.endswith(".am") or f in ("configure", "aclocal.m4", "config.h.in"):
                    try:
                        os.utime(os.path.join(root, f), None)
                    except OSError:
                        pass  # HMDFS may have read-only files, timestamps not critical
        # Fix execute permissions lost during zip extraction on OHOS/HMDFS
        scripts = ["configure", "config.guess", "config.sub", "install-sh",
                   "depcomp", "mkinstalldirs", "ylwrap", "missing", "compile"]
        for script in scripts:
            path = os.path.join(self.source_folder, script)
            if os.path.exists(path):
                os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        autotools = Autotools(self)
        autotools.configure()
        # Patch the 'missing' script to always exit 0. On OHOS, automake-1.16
        # is not available, but the pre-generated Makefile.in/configure don't
        # need regeneration. The missing script fails because the shell tries
        # to exec the missing tool directly (exit 127), not via exit statements.
        missing_path = os.path.join(self.source_folder, "missing")
        if os.path.exists(missing_path):
            with open(missing_path, "w") as f:
                f.write("#!/bin/sh\n# Stub: tools not available on OHOS, files pre-generated\nexit 0\n")
            os.chmod(missing_path, os.stat(missing_path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # gsoap provides multiple library variants in lib/:
        # libgsoap.a (C base), libgsoap++.a (C++ base)
        # libgsoapck.a (C+cookies), libgsoapck++.a (C+++cookies)
        # libgsoapssl.a (C+SSL), libgsoapssl++.a (C+++SSL)
        # The base gsoap library is the primary consumer-facing library.
        # Other variants are available in the package lib/ directory.
        self.cpp_info.libs = ["gsoap"]
        # gsoap also ships executables (soapcpp2, wsdl2h)
        self.cpp_info.bindirs = ["bin"]
