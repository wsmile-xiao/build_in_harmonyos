#!/usr/bin/env python3
"""Conan recipe — cdpr 2.4 (Makefile, binary tool).

cdpr (Cisco Discovery Protocol Reporter) listens on a network interface
for CDP packets and decodes them. Upstream ships a plain Makefile with
no configure step and no test suite; the only build input besides the
C sources is libpcap.
"""

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class CdprConan(ConanFile):
    name = "cdpr"
    version = "2.4"
    description = "Cisco Discovery Protocol Reporter"
    license = "GPL-2.0-or-later"
    homepage = "https://cdpr.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpcap/1.10.6")

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "cdpr %s only supports Linux and OHOS, got os=%s" % (self.version, self.settings.os)
            )

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        # Upstream Makefile hardcodes `gcc` and fixed CFLAGS/LDFLAGS; patch
        # 0001 switches the link line to $(CC) so the Conan toolchain compiler
        # is honored. CFLAGS/LDFLAGS passed on the make command line override
        # the Makefile assignments; keep upstream -Wall -W -O2 and append the
        # libpcap include/lib dirs from the Conan dependency (dhcpdump precedent).
        incs = " ".join("-I%s" % d for d in self.dependencies["libpcap"].cpp_info.includedirs)
        libdirs = " ".join("-L%s" % d for d in self.dependencies["libpcap"].cpp_info.libdirs)
        cflags = "-Wall -W -O2 %s" % incs
        ldflags = "%s -lpcap" % libdirs
        self.run('cd "%s" && make CC=%s "CFLAGS=%s" "LDFLAGS=%s" -j1' % (
            self.source_folder, cc, cflags, ldflags))
        # Upstream ships no test suite: the Makefile defines only the `cdpr`
        # and `clean` targets (audited, see test_package/MANIFEST.yml), so
        # there is no `make check` to run here. Functional verification is
        # done by test_package executing the real cdpr binary.

    def package(self):
        copy(self, "cdpr", self.source_folder, str(self.package_folder) + "/bin")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
