#!/usr/bin/env python3
"""Conan recipe for ldap2zone 0.2 - create DNS zone files from LDAP data.

ldap2zone reads the records of one DNS zone stored in an LDAP directory
(dnszone schema, as used by BIND with an LDAP back-end) and prints a plain
ASCII zone file to stdout. A companion shell script, ldap2bind, regenerates
BIND configuration and zone files from LDAP.

OHOS notes
----------
* Upstream is a single C file plus a 3-line Makefile with no configure,
  install or check targets (``gcc -Wall ldap2zone.c -o ldap2zone -lldap
  -llber``). The recipe compiles that exact command in build() with the
  compiler taken from ``tools.build:compiler_executables`` (R33) instead
  of patching the hard-coded ``gcc``, so no patches/ directory is needed.
* Links against openldap/2.6.7 (``-lldap -llber``). Only the modern LDAP
  API (ldap_initialize / ldap_search_ext / ldap_result / ...) is used, so
  no LDAP_DEPRECATED guard is required (unlike ldap2dns 0.3.1).
* Upstream ships no tests (no tests/ directory, no check/test make
  target): build() runs a live R51 audit and records
  HMBS_UPSTREAM_TEST_RESULT with status no_tests.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class Ldap2zoneConan(ConanFile):
    name = "ldap2zone"
    version = "0.2"
    description = "Create DNS zone files from LDAP dnszone information"
    license = "ISC"
    homepage = "https://salsa.debian.org/debian-edu-pkg-team/ldap2zone"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ldap2zone OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def requirements(self):
        self.requires("openldap/2.6.7")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        ldap = self.dependencies["openldap"]
        inc_dir = os.path.join(ldap.package_folder, "include")
        lib_dir = os.path.join(ldap.package_folder, "lib")

        # R33: compiler from Conan conf, never from bare shell env vars.
        cc = self._compiler("c", "clang")

        # Upstream build line verbatim (Makefile: gcc -Wall ldap2zone.c -o
        # ldap2zone -lldap -llber), with compiler/include/lib injected.
        self.run(
            "{cc} -Wall -O2 -I\"{inc}\" ldap2zone.c -o ldap2zone "
            "-L\"{lib}\" -lldap -llber".format(cc=cc, inc=inc_dir, lib=lib_dir),
            cwd=self.source_folder)

        # R51 upstream test audit (live, evidence stays in the log): the 0.2
        # tarball has no tests/ directory and its Makefile defines no
        # check/test target, so there is nothing to execute.
        self.run(
            "ls tests 2>/dev/null || echo 'AUDIT: no tests/ directory'; "
            "grep -E '^(check|test)[^:]*:' Makefile "
            "|| echo 'AUDIT: no check/test target in Makefile'",
            cwd=self.source_folder)
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "no_tests",
            "framework": "none",
            "command": "ls tests; grep check/test targets in Makefile (R51 audit)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "ldap2zone 0.2 tarball holds 8 files "
                      "(ldap2zone.c/Makefile/ldap2bind/man pages/changelog/html), "
                      "no tests/ directory and no check/test make target",
        }))

    def package(self):
        top = self.source_folder
        copy(self, "ldap2zone", top, os.path.join(self.package_folder, "bin"))
        copy(self, "ldap2bind", top, os.path.join(self.package_folder, "bin"))
        copy(self, "ldap2zone.1",
             top, os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "ldap2bind.1",
             top, os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        # application package: consumers use the ldap2zone/ldap2bind binaries
        self.cpp_info.bindirs = ["bin"]
