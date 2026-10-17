#!/usr/bin/env python3
"""Conan recipe — isochron 0.9

NXP isochron: a Linux TSN (time-sensitive networking) tool used to
measure and orchestrate 802.1Qbv/Qav traffic (daemon, orchestrate,
send, rcv, report subcommands sharing one binary through symlinks).
Build system: plain kernel-style Makefile (pkg-config probes libmnl,
pandoc builds man pages — skipped, OHOS has no pandoc).
License: GPL-2.0-only.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches

CC_FALLBACK = "/data/service/hnp/bin/clang"


class IsochronConan(ConanFile):
    name = "isochron"
    version = "0.9"
    description = ("isochron: Linux TSN tool to measure and orchestrate "
                   "time-sensitive (802.1Qbv) traffic")
    license = "GPL-2.0-only"
    homepage = "https://github.com/NXP/isochron"
    url = "https://github.com/NXP/isochron"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libmnl/1.0.5")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # OHOS SDK 26 sysroot defect shims: the UAPI linux/socket.h defines
        # struct sockaddr_storage unguarded, clashing with musl's
        # sys/socket.h (same for linux/if_ether.h vs netinet/if_ether.h).
        # Shadow both headers with musl-backed equivalents via -I order.
        shim = os.path.join(self.build_folder, "shim", "linux")
        os.makedirs(shim, exist_ok=True)
        with open(os.path.join(shim, "socket.h"), "w", encoding="utf-8") as f:
            f.write(
                "/* OHOS SDK 26 shim: musl sys/socket.h and UAPI linux/socket.h\n"
                " * both define struct sockaddr_storage.  Shadow the UAPI header\n"
                " * with the musl definition plus the kernel type still needed. */\n"
                "#ifndef ISO_OHOS_LINUX_SOCKET_SHIM\n"
                "#define ISO_OHOS_LINUX_SOCKET_SHIM\n"
                "#include <sys/socket.h>\n"
                "typedef unsigned short __kernel_sa_family_t;\n"
                "#endif\n")
        with open(os.path.join(shim, "if_ether.h"), "w", encoding="utf-8") as f:
            f.write(
                "/* OHOS shim: route linux/if_ether.h to the musl netinet\n"
                " * definition so struct ethhdr has a single definer. */\n"
                "#ifndef ISO_OHOS_LINUX_IF_ETHER_SHIM\n"
                "#define ISO_OHOS_LINUX_IF_ETHER_SHIM\n"
                "#include <netinet/if_ether.h>\n"
                "#endif\n")
        compilers = self.conf.get("tools.build:compiler_executables") or {}
        self._cc = compilers.get("c", CC_FALLBACK)

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # E386 pattern: start from the healthy worktree cwd and let the shell
        # cd internally (the conan cache build dir trips HMDFS getcwd()).
        shim = os.path.join(self.build_folder, "shim")
        dep = self.dependencies["libmnl"]
        inc = os.path.join(dep.package_folder, dep.cpp_info.includedirs[0])
        lib = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
        self._mnl_inc, self._mnl_lib = inc, lib
        # `isochron` target only: the `all` target also builds man pages with
        # pandoc, which OHOS does not ship.  PKG_CONFIG is pointed at /bin/true
        # because libmnl comes from the Conan graph (flags passed explicitly),
        # and the Makefile hard-errors when `which pkg-config` fails.
        self.run(
            f'cd "{src}" && make -j1 isochron '
            f'CC="{self._cc}" PKG_CONFIG=/bin/true '
            f'CPPFLAGS="-I{shim}" '
            f'LIBMNL_CFLAGS="-I{inc}" LIBMNL_LDFLAGS="-L{lib} -lmnl"',
            env="conanbuild")

    def package(self):
        src = self.source_folder
        # install-binaries + install-completion only: install-manpages needs
        # the pandoc-generated pages that were not built.  The libmnl flags
        # must be passed again: the install targets re-evaluate the Makefile,
        # whose $(error) fires when the pkg-config probe comes up empty.
        self.run(
            f'cd "{src}" && make install-binaries install-completion '
            f'PKG_CONFIG=/bin/true '
            f'LIBMNL_CFLAGS="-I{self._mnl_inc}" LIBMNL_LDFLAGS="-L{self._mnl_lib} -lmnl" '
            f'DESTDIR="{self.package_folder}" prefix= bindir=/bin datarootdir=/share',
            env="conanbuild")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
