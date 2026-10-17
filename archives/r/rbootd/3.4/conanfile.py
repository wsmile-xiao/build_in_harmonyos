#!/usr/bin/env python3
"""Conan recipe — rbootd 3.4 (Remote Boot Daemon, binary tool).

rbootd is the HP Remote Boot Daemon: it serves the first stage of the boot
sequence to HP 9000 workstations over the network.  Upstream ships a plain
Makefile with two branches selected by `uname -s` (Linux uses the libpcap
packet-capture backend, BSD uses bpf); on HarmonyOS `uname -s` returns
"HarmonyOS" and the Makefile must be extended to take the Linux branch.
The program is a system daemon and has no configure step and no test suite;
its only external dependency is libpcap.
"""

import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class RbootdConan(ConanFile):
    name = "rbootd"
    version = "3.4"
    description = "Remote Boot Daemon for HP workstations (network bootstrap)"
    license = "BSD-4-Clause"
    homepage = "https://git.kernel.org/pub/scm/linux/kernel/git/deller/rbootd.git"
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

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "rbootd %s only supports Linux and OHOS, got os=%s"
                % (self.version, self.settings.os)
            )

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        # The upstream Makefile keeps `LFLAGS += -lpcap` and links with
        # `$(CC) -o $@ $(OBJS) $(LFLAGS) $(LDFLAGS)`; only the libpcap
        # include/lib search paths have to be supplied (dhcpdump/cdpr precedent).
        # CFLAGS/LDFLAGS on the make command line override the Makefile, so the
        # upstream -O2 -Wall values are repeated here.
        incs = " ".join("-I%s" % d for d in self.dependencies["libpcap"].cpp_info.includedirs)
        libdirs = " ".join("-L%s" % d for d in self.dependencies["libpcap"].cpp_info.libdirs)
        cflags = "-O2 -Wall -Wno-unused-variable %s" % incs
        # All three standard streams are detached inside the command: the
        # compiler silently exits 1 without producing any object file when it
        # inherits the caller's stdin (a socket under the OHOS agent) through
        # the `/bin/sh -> make -> /bin/sh` chain.  Feeding stdin from
        # /dev/null and redirecting the build output to a log file (replayed
        # below) keeps the real diagnostics and the exit code.  Note the
        # explicit `cd` instead of `cwd=`: passing `cwd=` also hits the HMDFS
        # getcwd quirk in the Conan cache tree.
        log = os.path.join(self.build_folder, "rbootd-build.log")
        cmd = ('cd "%s" && make CC=%s "CFLAGS=%s" "LDFLAGS=%s" -j1 '
               '< /dev/null > "%s" 2>&1'
               % (self.source_folder, cc, cflags, libdirs, log))
        ret = self.run(cmd, ignore_errors=True)
        if os.path.isfile(log):
            with open(log, "r", encoding="utf-8", errors="replace") as handle:
                for line in handle.read().splitlines():
                    self.output.info("build| %s" % line)
        if ret != 0:
            raise ConanException("rbootd build failed (make exit %s)" % ret)
        # Upstream ships no test suite: the Makefile defines only the
        # rbootd/clean/all/install/rbootd.8.gz targets (audited, see
        # test_package/MANIFEST.yml), so there is no `make check` to run here.
        # Functional verification is done by test_package executing the real
        # rbootd binary.

    def package(self):
        copy(self, "rbootd", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "rbootd.8", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man8"))
        copy(self, "rbootd.conf", os.path.join(self.source_folder, "etc-rbootd"),
             os.path.join(self.package_folder, "share", "rbootd"))
        copy(self, "copyright", os.path.join(self.source_folder, "debian"),
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
