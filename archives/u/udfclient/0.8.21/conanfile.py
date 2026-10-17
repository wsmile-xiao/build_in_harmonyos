#!/usr/bin/env python3
"""Conan recipe for udfclient 0.8.21 — UDF filesystem toolkit (OHOS PC adaptation).

udfclient (UDFtoolkit) is a self-contained C toolkit for UDF filesystems.
It builds six command line programs: the interactive `udfclient`, the
`udfdump` dumper, the `newfs_udf` formatter and the CD/MMC helpers
`cd_sessions`, `cd_disect` and `mmc_format`.  There are no third-party
dependencies: configure probes for libc/pthread/clock_gettime only and the
Linux SCSI backend uses the SDK provided scsi/sg.h.

OHOS adaptations (see patches/ and conandata.yml):
  - Makefile.in: BSD make `.TARGET` rules replaced with GNU make static
    pattern rules (the Conan/CI build drives GNU make).
  - config.guess: HarmonyOS detection (E007); otherwise configure aborts
    with "cannot guess build type".
  - config.sub: accepts the `linux-ohos` kernel-OS pair used by the OHOS
    Conan autotools toolchain host/build triplets (E205).
  - configure: `umask 077` removed from config.status temp-dir creation
    (E114 — HMDFS forces setgid and the drwx--S--- directory is not
    writable even by its owner).

Upstream test suite: none.  The tarball has no tests/ directory and
Makefile.in has no check/test target (see test_package/MANIFEST.yml for the
inventory evidence); adaptation consumer tests live in test_package/.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UdfclientConan(ConanFile):
    name = "udfclient"
    version = "0.8.21"
    description = "UDF filesystem toolkit (udfclient/udfdump/newfs_udf/cd_sessions/cd_disect/mmc_format)"
    license = "ClArtistic"  # Clarified Artistic License
    homepage = "https://www.13thmonkey.org/udfclient/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # CLI toolkit, not a library (R38: commands.json declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"udfclient is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        # E074: single job — parallel make tries to create the jobserver fifo
        # in TMPDIR and gets EPERM on HMDFS.
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Standalone binaries; no library interface is packaged.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
