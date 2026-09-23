#!/usr/bin/env python3
"""Conan recipe for PacketQ 1.7.3.

DNS-OARC's SQL-like frontend to pcap files (DNS traffic analyzer).  Pure
autotools TOOL package: the official dist tarball from dns-oarc.net ships a
pre-generated configure, so no autoreconf is needed at build time (the OHOS
device has no automake/libtoolize — probe-verified 2026-09-05).

OHOS machinery follows the gate-conformant archives/l/libxrandr/1.5.5
pattern: explicit GNU triplet (--build/--host) so config.guess never runs
(packetq's config.sub has zero ohos entries — grep-verified), umask
077->022 configure regeneration (packetq's configure contains exactly two
"umask 077" occurrences, same contract as libxrandr), /system/bin/sh with
CONFIG_SHELL, and a private TMPDIR (E002).

`make check` runs upstream's own regression suite — 8 golden-file tests
(src/test/test1-8.sh, registered TESTS, POSIX sh + diff -uw) covering the
SQL engine over bundled dns.pcap/dns6.pcap/sample.pcap.gz fixtures.  The
goldens read .gz pcaps, so zlib support (HAVE_LIBZ) is a hard test
requirement: zlib/1.3.1 is pinned (recipe+armv8 binary published on ohpcd,
verified 2026-09-05).  maxminddb stays optional upstream (PKG_CHECK failure
silently disables GeoIP) and is deliberately not introduced (R1).
"""

import os
import shlex
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class PacketqConan(ConanFile):
    name = "packetq"
    version = "1.7.3"
    description = "SQL-like frontend to PCAP files (DNS traffic analyzer)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/DNS-OARC/PacketQ"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Upstream src/test golden tests read pcap/sample.pcap.gz; gz pcap
        # support is compiled in only when configure finds libz.
        self.requires("zlib/1.3.1")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"packetq supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"])
        local_archive = os.getenv("PACKETQ_SOURCE_ARCHIVE")
        if local_archive:
            archive_path = Path(local_archive).resolve()
            if not archive_path.is_file():
                raise ConanException(
                    f"PACKETQ_SOURCE_ARCHIVE is not a regular file: {archive_path}"
                )
            source["url"] = archive_path.as_uri()
            source["filename"] = archive_path.name
        get(self, **source, strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.generate()
        # R33: toolchain-provided env only — no bare shell CFLAGS anywhere.

    def build(self):
        apply_conandata_patches(self)
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                self._generate_ohos_configure()
                self._configure_ohos()
                self._run_ohos("make -j1")
                # R51: upstream ships a REAL regression suite — eight
                # golden-file tests (src/test/test1-8.sh, automake TESTS)
                # exercising the SQL engine over dns.pcap/dns6.pcap/
                # sample.pcap.gz.  Running it here is the substantive
                # verification; a golden mismatch fails the build.
                self._run_ohos("make -j1 check")
            else:
                self.run("make -j1 check", cwd=self.build_folder)

    def package(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                destination = shlex.quote(self.package_folder)
                self._run_ohos(f"make -j1 install DESTDIR={destination}")
            else:
                self.run(f"make -j1 install DESTDIR={shlex.quote(self.package_folder)}",
                         cwd=self.build_folder)
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # Tool package (R38): commands.json at software level declares the
        # packetq command; no libraries, no consumer linkage.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        return environment

    def _configure_ohos(self):
        shell = "/system/bin/sh"
        if not os.path.isfile(shell):
            raise ConanInvalidConfiguration(f"OHOS configure shell is missing: {shell}")
        configure = self._ohos_configure_path()
        configure_args = [
            f"--srcdir={self.source_folder}",
            # build != host -> cross-compile mode: configure never EXECUTES
            # conftest binaries (libxrandr device-verified pattern); both
            # triplets explicit so config.guess never runs.  NOTE: this
            # dist's 2024-vintage config.sub REJECTS an `ohos` host suffix
            # outright (device-verified: "OS 'ohos' not recognized") even
            # when passed explicitly, so the host/build pair uses two
            # config.sub-clean triplets that still differ — cross mode is
            # what matters and the codebase branches nowhere on host_os.
            "--build=aarch64-unknown-linux-musl",
            "--host=aarch64-unknown-linux-gnu",
            # prefix=/ + DESTDIR=<package_folder> lands bin/ and share/
            # directly in the package root (the autotools default /usr/local
            # would nest them under usr/local/ — observed in the first G2
            # run; test_package then couldn't find bin/packetq).
            "--prefix=/",
        ]
        arguments = " ".join(shlex.quote(argument) for argument in configure_args)
        self._run_ohos(f'"{shell}" "{configure}" {arguments}')

    def _ohos_configure_path(self):
        return Path(self.build_folder, "configure-ohos")

    def _run_ohos(self, command):
        shell = "/system/bin/sh"
        prefix = f"export SHELL={shell} CONFIG_SHELL={shell}; "
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")

    def _generate_ohos_configure(self):
        upstream = Path(self.source_folder, "configure")
        if not upstream.is_file():
            raise ConanException(f"configure script is missing: {upstream}")
        generated = self._ohos_configure_path()
        content = upstream.read_text(encoding="utf-8")
        needle = "umask 077"
        if content.count(needle) != 2:
            raise ConanException("configure umask contract changed")
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.write_text(
            content.replace(needle, "umask 022"),
            encoding="utf-8",
            newline="\n",
        )
