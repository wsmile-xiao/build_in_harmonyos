#!/usr/bin/env python3
"""Conan recipe for tayga 0.9.2 — out-of-kernel stateless NAT64 daemon.

TAYGA is a userland stateless NAT64 implementation (RFC 6145) that exchanges
IPv4/IPv6 packets with the kernel through a TUN device.

OHOS adaptations (see conandata.yml patches + build() below):
  - tayga.h: skip linux/socket.h on OHOS (sockaddr_storage redefinition
    against musl sys/socket.h — knowledge entries E091/E119)
  - tayga.h: include sys/uio.h explicitly on OHOS (musl does not pull
    writev() in indirectly like glibc does)
  - build(): invoke configure via `sh configure` — on HMDFS the extracted
    script has no execute bit and chmod is ineffective (E046/E087), while
    sh only needs read access (approach proven on-device by kelbt 0.16)
  - build(): TMPDIR redirected to a writable dir on OHOS (/tmp is read-only, E002)

Notes:
  - Upstream has no test suite; upstream_test_in_build is false.
  - Running the daemon requires /dev/net/tun and root, which is out of scope
    for the Conan build; test_package runs a CLI smoke script instead.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain

class TaygaConan(ConanFile):
    name = "tayga"
    version = "0.9.2"
    description = "Out-of-kernel stateless NAT64 daemon for Linux (TAYGA)"
    license = "GPL-2.0-or-later"  # source headers: "version 2 ... or (at your option) any later version"
    homepage = "http://www.litech.org/tayga/"
    url = "https://salsa.debian.org/debian/tayga"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        # tayga builds in-source (configure at source root, as shipped)
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        # conandata lists the official upstream URL first and an identical-
        # sha256 mirror second; try them in order, so a transient upstream
        # outage (litech.org had one on 2026-10-01) falls through to the
        # Debian pool copy instead of blocking the build. (Explicit loop for
        # conan versions whose get() does not accept url lists.)
        last_error = None
        for src in self.conan_data["sources"]:
            try:
                get(self, url=src["url"], sha256=src["sha256"], strip_root=True)
                return
            except ConanException as exc:
                last_error = exc
        raise last_error

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            # E002: /tmp is read-only on HarmonyOS PC
            os.environ["TMPDIR"] = "/data/storage/el2/base/cache"
        # E046/E087: on HMDFS the configure script carries no execute bit and
        # chmod is ineffective; `sh configure` needs read access only.
        base_build = self.folders.base_build
        configure = os.path.join(base_build, "configure")
        self.run(f'sh "{configure}" --prefix=/ --bindir=/bin --sbindir=/bin', cwd=base_build, env="conanbuild")
        self.run("make -j1", cwd=base_build, env="conanbuild")

    def package(self):
        base_build = self.folders.base_build
        self.run(f'make install DESTDIR={self.package_folder}', cwd=base_build, env="conanbuild")
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin"]
