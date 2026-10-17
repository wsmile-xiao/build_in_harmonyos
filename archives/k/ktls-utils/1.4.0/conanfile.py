#!/usr/bin/env python3
"""Conan recipe - ktls-utils 1.4.0 for OpenHarmony PC (OHOS/aarch64).

ktls-utils provides `tlshd`, a user-space TLS handshake agent that services
in-kernel TLS (kTLS) handshake requests on behalf of kernel consumers. It is a
plain Autotools project (no libtool, no AC_CANONICAL_HOST) that installs a
single daemon (upstream `sbin_PROGRAMS = tlshd`; conan normalizes sbindir to
${prefix}/bin, so it packages to bin/tlshd) plus config files and man pages.

Adaptation notes (see notes.md for the full account):
  * Build inputs (gnutls / libkeyutils / libnl / glib) come from the ohpcd
    registry via PkgConfigDeps. <linux/tls.h> is provided by the OHOS SDK
    sysroot, and the net/handshake UAPI is vendored inside
    src/tlshd/netlink.h, so no kernel headers beyond <linux/tls.h> are needed
    to compile.
  * The keyutils conan package publishes pkg_config_name "keyutils", while the
    upstream configure script probes for the module "libkeyutils"; build()
    drops a libkeyutils.pc alias next to the generated keyutils.pc so
    PKG_CHECK_MODULES([LIBKEYUTILS], [libkeyutils]) resolves.
  * Session-tag support (the only user of libyaml) stays off, its default.
  * Upstream ships no test suite (no TESTS / check_PROGRAMS in any Makefile.am
    and no test scripts), so the package is verified with a consumer smoke
    test (test_package/test.sh) that exercises the packaged binary's
    kernel-independent code paths.
"""
import os
import time

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load, save
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class KtlsUtilsConan(ConanFile):
    name = "ktls-utils"
    version = "1.4.0"
    description = "TLS handshake agent (tlshd) for in-kernel TLS consumers"
    license = "GPL-2.0-only"
    homepage = "https://github.com/oracle/ktls-utils"
    url = "https://github.com/oracle/ktls-utils"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gnutls/3.8.10")
        self.requires("libkeyutils/1.6.3")
        self.requires("libnl/3.11.0")
        self.requires("glib/2.84.0.2")

    def build_requirements(self):
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        # github.com release-asset downloads intermittently stall past Conan's
        # connect timeout from here (the device is heavily loaded); the
        # autotools dist tarball (which carries the generated configure /
        # Makefile.in) is the only usable source because neither this device
        # nor the CI workers regenerate them. Outlast the stall with bounded
        # retries on the same verified URL; a checksum mismatch is never
        # retried.
        sources = self.conan_data["sources"]
        last = None
        for attempt in range(1, 9):
            try:
                get(self, **sources, strip_root=True)
                return
            except Exception as exc:
                last = exc
                text = str(exc).lower()
                if "checksum" in text or "sha256" in text:
                    raise
                self.output.warning(
                    "Source download failed (attempt %d/8): %s" % (attempt, exc))
                time.sleep(10 + 5 * attempt)
        raise Exception("ktls-utils source download failed after 8 attempts: %s" % last)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        self._libkeyutils_pc_alias()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def _libkeyutils_pc_alias(self):
        # configure.probes for pkg-config module "libkeyutils"; the conan
        # keyutils package emits "keyutils.pc". Copy it to libkeyutils.pc in
        # the same directory (pkg-config resolves by file name).
        for base in (os.path.join(self.generators_folder, "pkgconfig"),
                     self.generators_folder, self.build_folder):
            if not os.path.isdir(base):
                continue
            src = os.path.join(base, "keyutils.pc")
            if os.path.isfile(src):
                content = load(self, src)
                save(self, os.path.join(base, "libkeyutils.pc"), content)
                self.output.info("libkeyutils.pc alias written to %s" % base)
                return
        raise Exception("keyutils.pc not found to build libkeyutils.pc alias")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # conan's AutotoolsToolchain normalizes --sbindir to ${prefix}/bin, so
        # the `sbin_PROGRAMS` install target (tlshd) lands in bin/, not sbin/.
        self.cpp_info.bindirs = ["bin"]
        # tlshd is a dynamically-linked binary with no RUNPATH: it DT_NEEDEDs
        # libgnutls.so.30, but gnutls's cpp_info.libdirs is empty in this build,
        # so VirtualRunEnv does not put gnutls/p/lib on the consumer's
        # LD_LIBRARY_PATH (it does propagate libgcrypt/libtasn1/libgpg-error/libkeyutils).
        # Explicitly forward gnutls's runtime lib dir so downstream binaries
        # actually load.
        try:
            gnutls = self.dependencies["gnutls"]
        except Exception:
            gnutls = None
        if gnutls is not None:
            self.runenv_info.append_path(
                "LD_LIBRARY_PATH", os.path.join(gnutls.package_folder, "lib"))
