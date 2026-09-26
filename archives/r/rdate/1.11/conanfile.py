#!/usr/bin/env python3
"""Conan recipe — rdate 1.11 (openrdate, RFC 868 / SNTP time client).

Upstream ships autotools sources without a generated configure, so
autoreconf -fi runs in build().  The only adaptation is patches/0001:
upstream hard-requires <bsd/stdlib.h> (configure exits when it is
missing) for a single arc4random() call, but OHOS musl provides
arc4random() straight from <stdlib.h>, which ntp.c already includes —
the libbsd dependency is vestigial on this platform (link-probed).

No upstream test suite exists (Makefile.am wires no TESTS); the
consumer test drives the packaged binary through its CLI contract.
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
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class RdateConan(ConanFile):
    name = "rdate"
    version = "1.11"
    description = (
        "rdate: set or print the system time from an RFC 868 TCP or "
        "SNTP (NTP) server"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/resurrecting-open-source-projects/openrdate"
    url = ""  # CI fills this
    topics = ("time", "ntp", "rfc868", "cli")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # E178: the upstream tarball ships configure.ac only (no generated
        # configure), so build() bootstraps it with autoreconf -fi.  The CI
        # worker has the autoconf suite under /data/service/hnp/bin but no
        # automake/aclocal/libtoolize on PATH, so autoreconf dies there with
        # "Can't exec aclocal ... Autom4te/FileUtils.pm line 299" (rev
        # e8e55428, build 60453).  Pull complete automake + libtool in through
        # the build profile instead (enet / afuse / aircrack-ng pattern -
        # R33-safe, no hardcoded paths); tool_requires resolve against -pr:b,
        # which both ci/conan/build_and_test.sh and ohc-run conan-verify pass.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def _patch_autotools_aux_for_ohos(self, src):
        """Add the OHOS detection branches to generated config.guess/config.sub (E007).

        These are the same three insertions scripts/patch-autotools-ohos.pl
        makes on automake/1.18's 2024-07-27 scripts (verified by diff on-device).
        They are inlined because a recipe running from the Conan cache cannot
        reach that script: CI_REPO_ROOT is not part of the build environment.
        replace_in_file is strict, so a drifted upstream aux script fails the
        build loudly instead of silently skipping the patch.
        """
        guess = os.path.join(src, "config.guess")
        sub = os.path.join(src, "config.sub")
        replace_in_file(
            self, guess,
            "#if defined(__ANDROID__)\n\tLIBC=android\n",
            "#if defined(__ANDROID__)\n\tLIBC=android\n"
            "#elif defined(__OHOS__)\n    LIBC=ohos\n",
        )
        replace_in_file(
            self, guess,
            "in\n    *:NetBSD:*:*)",
            "in\n    *:HarmonyOS:*:*)\n"
            '\tcase "$UNAME_MACHINE" in\n'
            '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
            '\t    armv7*|armv8*) MACHINE=arm ;;\n'
            '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
            '\t    i?86)         MACHINE=i686 ;;\n'
            '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
            '\tesac\n'
            '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
            '\t;;\n\n'
            "    *:NetBSD:*:*)",
        )
        android = (
            "\t\t\tandroid-linux)\n"
            "\t\t\t\tbasic_machine=$field1-unknown\n"
            "\t\t\t\tbasic_os=linux-android\n"
            "\t\t\t\t;;\n"
        )
        replace_in_file(
            self, sub, android,
            android
            + "\t\t\tohos-linux)\n"
            "\t\t\t\tbasic_machine=$field1-unknown\n"
            "\t\t\t\tbasic_os=linux-ohos\n"
            "\t\t\t\t;;\n",
        )

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"rdate not validated for {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # No generated configure in the tarball; autoreconf under /bin/sh
        # (E386: the hnp bash cannot hold the HMDFS working directory, so
        # keep autoconf away from it entirely).
        self.run(
            "env -u CONFIG_SHELL SHELL=/bin/sh autoreconf -fi", cwd=src
        )
        # E007: autoreconf -fi installs automake/1.18's own config.guess and
        # config.sub (timestamp 2024-07-27), and neither knows this host:
        # uname -s returns "HarmonyOS" with "HongMeng Kernel 1.12.0", so the
        # build-type probe falls through to a compiler probe that cannot create
        # its dummy.c under HMDFS, and configure aborts with "cannot guess build
        # type; you must specify one".  Add the OHOS branches to those two
        # generated files here - they are not in the tarball, so a conandata
        # patch cannot reach them.  E007 rules out passing --build/--host
        # instead: that makes configure treat the build as a cross-compile and
        # skip every AC_RUN_IFELSE check.
        self._patch_autotools_aux_for_ohos(src)
        # E011/E114: HMDFS cannot write the 0700-mode temp dirs configure
        # creates via `umask 077` ("could not setup config files
        # machinery"). Drop the umask wrapper, keep the temp dir creation.
        replace_in_file(self, f"{src}/configure", "umask 077 && ", "")
        self.run(
            "env -u CONFIG_SHELL SHELL=/bin/sh "
            f'./configure --prefix="{self.package_folder}"',
            cwd=src,
        )
        self.run("env -u CONFIG_SHELL SHELL=/bin/sh make -j2", cwd=src)

    def package(self):
        self.run(
            "env -u CONFIG_SHELL SHELL=/bin/sh make install",
            cwd=self.source_folder,
        )
        for license_file in ("LICENSE", "COPYING"):
            copy(self, license_file, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"),
                 keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
