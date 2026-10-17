#!/usr/bin/env python3
"""Conan recipe for blockdomains 0.1 — block list based domain name filtering.

blockdomains is a standalone daemon that filters network traffic through
iptables NFQUEUE (libnetfilter_queue). Upstream uses a plain Makefile that
embeds dpkg-buildflags (Debian-only), so this recipe bypasses make and
compiles the three C sources directly with the toolchain compiler.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class BlockdomainsConan(ConanFile):
    name = "blockdomains"
    version = "0.1"
    description = "Block list based domain name filtering for iptables via libnetfilter-queue"
    license = "GPL-3.0-or-later"
    homepage = "https://git.rrq.au/rrq/blockdomains.git"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # Patches must be exported with the recipe so apply_conandata_patches
        # can find them in the export sources folder (Conan 2 pattern).
        export_conandata_patches(self)

    def requirements(self):
        # Upstream links with -lnetfilter_queue; libnetfilter_queue provides
        # the NFQUEUE user-space API (nfq_open/nfq_create_queue/...).
        self.requires("libnetfilter_queue/1.0.5")

    def validate(self):
        # R32: must check in ("Linux", "OHOS"), not == "Linux".
        # NFQUEUE packet filtering is Linux-family functionality only.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "blockdomains only supports Linux/OHOS, not " + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def generate(self):
        # R33: compiler/flags come from the Conan toolchain graph (CC, CPPFLAGS,
        # CFLAGS, LDFLAGS via conanbuild env), never bare shell variables.
        tc = AutotoolsToolchain(self)
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _deps_env(self):
        """Collect include/lib dirs from all direct AND transitive deps.

        libnetfilter_queue.h #includes <libnfnetlink/libnfnetlink.h>, so the
        consumer TU also needs the transitive libnfnetlink/libmnl include
        dirs; collecting only the direct dependency broke compilation
        (fatal error: 'libnfnetlink/libnfnetlink.h' file not found, ci-run2).
        """
        inc = []
        lib = []
        for dep in self.dependencies.values():
            cpp = dep.cpp_info
            inc.extend(cpp.includedirs)
            lib.extend(cpp.libdirs)
        return inc, lib

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OS {self.settings.os} not supported, requires Linux or OHOS"
            )
        apply_conandata_patches(self)

        top = self.source_folder
        out = self.build_folder
        inc, lib = self._deps_env()
        inc_flags = " ".join("-I" + str(p) for p in inc)
        lib_flags = " ".join("-L" + str(p) for p in lib)

        # Upstream test evidence: the Makefile only defines default/install/
        # clean targets — there is no check target and no test suite.
        self.run(f"cd {top} && make -n check 2>&1 || true", env="conanbuild")

        # Upstream Makefile embeds dpkg-buildflags (Debian-only), so compile
        # the three sources directly with the toolchain compiler.
        for src in ("blockdomains.c", "cache.c", "database.c"):
            self.run(
                f"cd {out} && $CC $CPPFLAGS $CFLAGS {inc_flags} "
                f"-c {top}/src/{src} -o {src}.o",
                env="conanbuild",
            )
        # Link the objects produced above; their names carry the full source
        # suffix ("blockdomains.c.o"), matching the -o names of the compile
        # loop (mismatch broke the link step in ci-run3).
        # libnetfilter_queue ships as a static archive, so its own dependency
        # libnfnetlink (nfnl_*/nlif_* symbols) must be linked explicitly after
        # it (undefined nfnl_* in ci-run4).
        self.run(
            f"cd {out} && $CC $CFLAGS blockdomains.c.o cache.c.o database.c.o "
            f"-o blockdomains $LDFLAGS {lib_flags} -lnetfilter_queue -lnfnetlink",
            env="conanbuild",
        )

    def package(self):
        # Upstream installs blockdomains to /usr/sbin and blockdomainsctl to
        # /usr/bin; both are placed in bin/ for CI L2/L5 compatibility.
        # The Makefile install target is NOT used: it depends on man pages
        # that require asciidoctor and are not part of this port.
        copy(self, "blockdomains", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        ctl = os.path.join(self.package_folder, "bin", "blockdomainsctl")
        shutil.copy2(
            os.path.join(self.source_folder, "blockdomainsctl"), ctl
        )
        os.chmod(ctl, 0o755)

    def package_info(self):
        # blockdomains is a standalone binary, not a library.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
