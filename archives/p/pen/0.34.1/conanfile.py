#!/usr/bin/env python3
"""Conan recipe for pen 0.34.1 — load balancer for udp and tcp based protocols.

pen lets several back-end servers appear as one to the outside. It keeps a
client table so a returning client lands on the same server (session affinity),
detects dead servers and fails over, and can proxy TLS when built with OpenSSL.

Build system: autotools. The upstream release tarball ships a pre-generated
``configure`` (autoconf 2.69) plus ``Makefile.in``; it does NOT ship
``config.guess``/``config.sub``, therefore the build triplet is pinned
explicitly via ``--build`` so the guess probe is never invoked (same approach
as ``archives/n/ngircd/28``).

Dependencies: ``openssl/3.5.8.1`` (static). OpenSSL is what the upstream
``configure --with-ssl`` probe looks for; without it ``ssl.c`` compiles to an
empty translation unit and pen loses its TLS front-end/back-end support.
``libgeoip`` and ``libnetmap`` (DSR) are not published to the ohpcd registry,
so both features are switched off explicitly (see notes.md).
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PenConan(ConanFile):
    name = "pen"
    version = "0.34.1"
    description = ("pen 0.34.1 - load balancer for udp and tcp based protocols "
                   "such as dns, http or smtp")
    license = "GPL-2.0-or-later"
    homepage = "https://siag.nu/pen/"
    url = "https://siag.nu/pub/pen/pen-0.34.1.tar.gz"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Only dependency: OpenSSL, needed for pen's TLS front/back ends.
        # Verified consumable from ohpcd before the adaptation started (W0/R36).
        self.requires("openssl/3.5.8.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--with-ssl",
            # libgeoip is not published to the ohpcd registry; GeoIP country
            # lookup is an optional accounting feature, so it stays off.
            "--without-geoip",
            # DSR needs linux/if_packet.h + net/netmap_user.h (netmap), which
            # have no OHOS counterpart; the plain proxy modes are unaffected.
            "--without-dsr",
            # Upstream enables -DDEBUGGING by default; a release package must
            # not spam syslog/stderr with per-request debugging dumps.
            "--disable-debugging",
            # The release tarball has no config.guess; pin the triplet so the
            # probe is skipped entirely (uname -s is "HarmonyOS").
            "--build=aarch64-linux-ohos",
        ])
        tc.generate()
        # Conan 2.29's AutotoolsToolchain does not forward dependency -I/-L,
        # so AutotoolsDeps is what makes openssl visible to the configure
        # probes (HAVE_LIBSSL/HAVE_EC_KEY) and to the final link.
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # OHOS fix: on the CI workers the conan cache lives on HMDFS
        # (/storage/Users/...), where the 0700 directory created by
        # `mktemp -d "./confXXXXXX"` cannot be written back by the very
        # process that created it (uid mapping): config.status dies with
        # "./confXXXXXX/subs1.awk: Permission denied". The tmp-dir block sits
        # inside a quoted heredoc, so patching this one spot in `configure`
        # fixes BOTH configure itself and the config.status it generates.
        # Same inline replacement as archives/4/4ti2/1.6.10 (merged
        # precedent): plain mkdir under the default umask instead of mktemp.
        if self.settings.os == "OHOS":
            _configure = os.path.join(self.source_folder, "configure")
            if os.path.exists(_configure):
                with open(_configure, "r", encoding="utf-8",
                          errors="ignore") as f:
                    _text = f.read()
                _old = ('tmp=`(umask 077 && mktemp -d "./confXXXXXX") '
                        '2>/dev/null` &&\n  test -d "$tmp"')
                _new = ('tmp="./conf$$-$RANDOM"\n  (mkdir "$tmp" '
                        '2>/dev/null)\n  test -d "$tmp"')
                if _old in _text:
                    _text = _text.replace(_old, _new)
                    with open(_configure, "w", encoding="utf-8") as f:
                        f.write(_text)
                    self.output.info("OHOS fix: configure mktemp->mkdir "
                                     "patch applied (HMDFS 0700 tmpdir)")
                else:
                    self.output.warn("OHOS mktemp patch: pattern not found "
                                     "in configure (upstream text may have "
                                     "changed); build may fail on HMDFS")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # `make check` is the only test entry point upstream declares. The
        # release bundle registers no TESTS/check_PROGRAMS, so automake's
        # check-am expands to an empty target — invoking it anyway is what
        # makes the "upstream tests were actually run" claim verifiable
        # (reports/upstream-test-run.log) instead of merely asserted.
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
