#!/usr/bin/env python3
"""Conan recipe for ldap2dns 0.3.1 — C CLI tool built with a plain Makefile.

Build: make (no configure script). Links against openldap/2.6.7
(-lldap -llber). Produces three runtime artifacts:
  ldap2dns, ldap2dnsd (same binary, argv[0]-detected daemon), ldap2tinydns-conf.
Adapted for HarmonyOS OHOS (aarch64-unknown-linux-ohos).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Ldap2dnsConan(ConanFile):
    name = "ldap2dns"
    version = "0.3.1"
    description = "ldap2dns — generate tinydns/named data files from an LDAP directory"
    license = "GPL-2.0-or-later"
    homepage = "https://packages.debian.org/source/ldap2dns"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openldap/2.6.7")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        ldap = self.dependencies["openldap"]
        inc_dir = os.path.join(ldap.package_folder, "include")
        lib_dir = os.path.join(ldap.package_folder, "lib")

        # R33: compiler from Conan conf, never from bare shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        # ldap2dns 0.3.1 uses the legacy LDAP API (ldap_init / ldap_simple_bind_s /
        # ldap_search_s / ...). OpenLDAP 2.6 still exports these symbols from
        # libldap but hides the declarations behind the LDAP_DEPRECATED guard,
        # so we must define LDAP_DEPRECATED=1 (verified on OHOS).
        inc = "-I{0} -DLDAP_DEPRECATED=1".format(inc_dir)
        ldflags = "-L{0}".format(lib_dir)
        self.run(
            "make CC='{cc} -O2' CCDEBUG='{cc} -g' LD='{cc}' "
            "INC='{inc}' LDFLAGS='{ldflags}' -j1".format(
                cc=cc, inc=inc, ldflags=ldflags),
            cwd=self.source_folder)

    def package(self):
        top = self.source_folder
        copy(self, "ldap2dns", top, os.path.join(self.package_folder, "bin"))
        copy(self, "ldap2dnsd", top, os.path.join(self.package_folder, "bin"))
        copy(self, "ldap2tinydns-conf",
             top, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # application package: consumers use the ldap2dns/ldap2dnsd binaries
        self.cpp_info.bindirs = ["bin"]
