#!/usr/bin/env python3
"""Conan recipe — avahi-unbound 0.9_rc5 (config-only package).

Provides the unbound DNS resolver configuration file for avahi mDNS
integration. The config file (avahi.conf) tells unbound to forward ".local"
zone queries to the avahi-daemon DNS proxy on 127.0.0.1:5354, and to treat
the ".local" domain as insecure (no DNSSEC) since mDNS is inherently
unauthenticated.

The config file content originates from the Alpine Linux aports repository
(main/avahi/unbound.conf), not from the avahi upstream source tarball. The
avahi source is used for version consistency and sha256 verification (same
source as avahi-compat-libdns_sd and avahi-glib subpackages).

This package produces no binaries or libraries — only a configuration file
installed to etc/unbound/unbound.conf.d/avahi.conf.

Upstream tests: none. The avahi source tarball has no tests for the unbound
integration config file; the Alpine APKBUILD's check() runs make check on
the full avahi project (daemon, libs) but not on this subpackage. Custom
tests are provided in test_package/ to validate the config file content.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class AvahiUnboundConan(ConanFile):
    name = "avahi-unbound"
    version = "0.9_rc5"
    description = "Unbound DNS resolver configuration for avahi mDNS integration"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/avahi/avahi"
    url = "https://github.com/avahi/avahi"
    package_type = "unknown"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # The config file content originates from Alpine Linux aports
        # (main/avahi/unbound.conf). It configures unbound to forward ".local"
        # zone queries to avahi-daemon's DNS proxy on 127.0.0.1:5354, and
        # to treat ".local" as insecure (no DNSSEC for mDNS).
        config_content = (
            'forward-zone:\n'
            '\tname: "local"\n'
            '\tforward-addr: 127.0.0.1@5354\n'
            'server:\n'
            '\tdo-not-query-localhost: no\n'
            '\tdomain-insecure: "local"\n'
        )
        out = os.path.join(self.build_folder, "avahi.conf")
        with open(out, "w", encoding="utf-8") as f:
            f.write(config_content)

        # No upstream tests exist for this config-only subpackage.
        # The avahi source has no avahi-unbound directory; the config file is
        # maintained by the Alpine Linux project in the aports repository.
        upstream = {
            "status": "skip",
            "framework": "none",
            "command": "",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "Config-only package (unbound config file for avahi "
                      "integration); no upstream tests exist for this "
                      "subpackage. Custom tests in test_package/ validate "
                      "config file content and structure (7 assertions).",
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
                upstream, ensure_ascii=False))

    def package(self):
        target = os.path.join(self.package_folder, "etc", "unbound",
                              "unbound.conf.d")
        copy(self, "avahi.conf", self.build_folder, target, keep_path=False)
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Config-only package: no libraries or executables.
        # Provides etc/unbound/unbound.conf.d/avahi.conf that integrates
        # avahi mDNS with unbound DNS resolver.
        pass
