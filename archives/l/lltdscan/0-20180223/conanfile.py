#!/usr/bin/env python3
"""Conan recipe — lltdscan 0-20180223 (Makefile, binary tool).

lltdscan sends a broadcast LLTD (Link Layer Topology Discovery) request on a
network interface and prints the neighbours that answered. It is a layer-2
scanner: it crafts the Ethernet frame with libnet and listens for the replies
with libpcap.

Upstream shape: a single hand-written Makefile (no configure/autotools/CMake)
over exactly two C files (lltdscan.c plus lltd.c, which is #included by the
former), plus a man page. No test suite of any kind.

Version note: upstream zed-0xff/lltdscan has NO tags and NO releases — the git
history stops at commit 258dbb1c7f86 (2013-02-04) and the AUR package is named
lltdscan-git for exactly that reason. `0-20180223` is therefore the
competition-platform-assigned version label required by task #8518, not an
upstream release string. The recipe pins the authoritative upstream master HEAD
(258dbb1c7f8672c09a4a578fc17dada524c3eabb) by commit SHA in conandata.yml so
the build stays reproducible; see notes.md §1 for the full derivation.

OHOS adaptation: no source patch is needed. The upstream Makefile already
compiles through the `$(CC)` variable (`$(CC) $(CFLAGS2) $(LDFLAGS2) -o lltdscan
lltdscan.c -lnet -lpcap -lrt`), so `make CC=<toolchain clang>` is enough to
honor the Conan toolchain. The only remaining obstacle is that CFLAGS2/LDFLAGS2
are hardcoded to /usr/local, /usr/include/pcap and /opt/csw (arping/Solaris
leftovers); those are overridden on the make command line with the Conan
dependency folders, the same way cdpr/2.4 and dhcpdump/1.10 do it.
"""

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class LltdscanConan(ConanFile):
    name = "lltdscan"
    version = "0-20180223"
    description = "Scan for LLTD (Link Layer Topology Discovery) enabled hosts on a network"
    license = "Unlicense"
    homepage = "https://github.com/zed-0xff/lltdscan"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("libpcap/1.10.6")
        self.requires("libnet/1.2")

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "lltdscan is only supported on Linux/OHOS, not " + str(self.settings.os)
            )

    def build(self):
        # Upstream hardcodes CC=gcc and points CFLAGS2/LDFLAGS2 at /usr/local,
        # /usr/include/pcap and /opt/csw (arping/Solaris leftovers). Make
        # command-line assignments override both, so the Conan toolchain
        # compiler and the Conan dependency folders are what actually get used.
        # -O2 is added on top of upstream's bare -g to match the other recipes
        # in this repo; the library flags stay on the upstream link line
        # (-lnet -lpcap -lrt) and are only repeated here to pin their order.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        incs = []
        libdirs = []
        for dep in (self.dependencies["libpcap"], self.dependencies["libnet"]):
            incs += ["-I%s" % d for d in dep.cpp_info.includedirs]
            libdirs += ["-L%s" % d for d in dep.cpp_info.libdirs]
        cflags2 = "-g -O2 %s" % " ".join(incs)
        ldflags2 = "-g %s" % " ".join(libdirs)
        self.run(
            'cd "%s" && make CC=%s "CFLAGS2=%s" "LDFLAGS2=%s" -j1'
            % (self.source_folder, cc, cflags2, ldflags2)
        )
        # Upstream ships no test suite: the Makefile defines only the `all`,
        # `lltdscan`, `clean`, `doc`, `install` and `dist` targets and there is
        # no check/test/TESTS target (audited, see test_package/MANIFEST.yml),
        # so there is nothing to run here. Functional verification is done by
        # test_package executing the real lltdscan binary.

    def package(self):
        copy(self, "lltdscan", self.source_folder, str(self.package_folder) + "/bin")
        copy(self, "lltdscan.8", self.source_folder,
             str(self.package_folder) + "/share/man/man8")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]