#!/usr/bin/env python3
"""Conan recipe — thrulay 0.9 (Autotools).

thrulay is a client/server network capacity and performance measurement tool
from Internet2: the `thrulayd` server opens TCP/UDP test streams and the
`thrulay` client measures throughput, one-way delay and loss against it.
The package ships both executables plus the libthrulay static library and
headers (src/client.h, src/server.h) for embedding the protocol.

Upstream: https://downloads.sourceforge.net/project/thrulay/thrulay/0.9/thrulay-0.9.tar.gz

Adaptation notes (full exploration log in notes.md):
  * config.guess/config.sub shipped upstream are the 2006-07-02 vintage and
    predate HarmonyOS/aarch64: configure dies with "cannot guess build type;
    you must specify one". Both files are replaced by the autoconf 2.72
    versions plus HarmonyOS identification (patch 0001/0002), and config.sub
    additionally accepts the linux-ohos kernel/OS pair. The E007 helper
    patch-autotools-ohos.pl cannot be used on this tarball (its anchor
    context does not match the 2006 scripts, 1/5 hunks applied).
  * configure carries `umask 077`: combined with HMDFS setgid directories the
    config.status temp dirs become drwx--S--- and the run fails with
    "mv: bad './confXXXXXX/config.h': Permission denied" (E114). Patch 0003
    drops the umask statement.
  * No third-party dependencies: every libc/libm/librt/libresolv symbol the
    sources need (log, nanosleep, herror, gethostbyname, socket,
    pthread_create, ...) is exported by the OHOS sysroot (verified
    symbol-by-symbol, see notes.md).
  * Deliverables are the two executables, so libthrulay is linked statically
    into them (--enable-static --disable-shared): the installed binaries then
    carry no runtime dependency on a self-shipped .so whose absolute libtool
    RUNPATH would not be portable. Consumers still get libthrulay.a via
    cpp_info.
  * Upstream ships no test suite (configure.ac has no AC_CONFIG_TESTDIR and
    `make check` reports "Nothing to be done"); test_package therefore
    implements consumer tests: CLI smoke test, a libthrulay API consumer, and
    a loopback thrulayd/thrulay end-to-end measurement.
"""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ThrulayConan(ConanFile):
    name = "thrulay"
    version = "0.9"
    description = (
        "Client/server network capacity and performance measurement tool from "
        "Internet2; measures TCP/UDP throughput, one-way delay and loss "
        "(thrulayd server + thrulay client + libthrulay)"
    )
    license = "BSD-3-Clause"  # per LICENSE (Internet2, 2006)
    homepage = "https://sourceforge.net/projects/thrulay/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/t/thrulay/0.9"

    package_type = "application"  # ships the thrulay/thrulayd CLI tools
    languages = "C"

    # The deliverables are executables plus a static library; there is no
    # shared/static option because libthrulay is always built static.
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Static-only: the two executables embed libthrulay, so the packaged
        # CLI is self-contained (no self-shipped .so + absolute RUNPATH).
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # E525: OHOS SELinux denies user-created FIFOs, so the GNU make
        # jobserver (which allocates a FIFO per job) must stay disabled.
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # 上游 Makefile.am 将两个可执行文件都装进 $(bindir)（实测：bin/thrulay,
        # bin/thrulayd；man 页分列 man1/thrulay.1 与 man8/thrulayd.8）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = ["thrulay"]
