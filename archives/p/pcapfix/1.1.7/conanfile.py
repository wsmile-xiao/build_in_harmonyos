#!/usr/bin/env python3
"""Conan recipe — pcapfix 1.1.7 — plain Makefile CLI tool (no configure).

pcapfix repairs damaged or corrupted pcap and pcapng capture files: it scans
for a broken pcap/pcapng global header, reconstructs it from packet-structure
heuristics and repairs corrupted packet headers.

Upstream: https://github.com/Rup0rt/pcapfix (author page https://f00l.de/pcapfix/)
Build system: plain Makefile — single binary `pcapfix`, libc only, no deps.

OHOS notes:
- legacy BSD types u_int8_t..u_int64_t (used in pcap.h/pcap_kuznet.h/pcapng.c)
  exist on glibc but not on musl — patched in pcapfix.h (patches/0001)
- upstream default CFLAGS contain gcc/coreutils-specific pieces
  (`--param=ssp-buffer-size=4`, `$(shell getconf LFS_CFLAGS)`), so the full
  flag set is passed explicitly via a make command-line variable
- upstream `make install` uses GNU-only `install -pDm…`, so packaging is done
  manually (binary + man page + GPLv3 license text)
- upstream ships no test target (see test_package/MANIFEST.yml); the packaged
  binary is functionally smoke-tested in test_package
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PcapfixConan(ConanFile):
    name = "pcapfix"
    version = "1.1.7"
    description = "Repair damaged or corrupted pcap and pcapng files"
    license = "GPL-3.0-or-later"
    homepage = "https://f00l.de/pcapfix/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: explicit allow-list instead of == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pcapfix supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def requirements(self):
        pass  # libc only — no external dependencies (all includes are standard headers)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        # R33: compiler from Conan conf, never a bare env var
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict)
        return compilers.get("c", "clang") if compilers else "clang"

    def build(self):
        apply_conandata_patches(self)
        cc = self._cc()
        # Upstream CFLAGS default to
        #   "$(shell getconf LFS_CFLAGS) -D_FORTIFY_SOURCE=2 -O2 -fstack-protector
        #    --param=ssp-buffer-size=4 -Wall -Wextra -std=gnu99 -pedantic
        #    -Wformat -Werror=format-security -g"
        # `getconf` may be absent on OHOS and clang rejects gcc's `--param=`,
        # so pass the whole flag set explicitly (a command-line make variable
        # fully overrides the Makefile's CFLAGS). The Makefile's own
        # `LDFLAGS += -Wl,-z,relro` (non-Darwin/Cygwin branch) stays in effect
        # because LDFLAGS is not overridden here.
        cflags = ("-O2 -Wall -Wextra -std=gnu99 -pedantic "
                  "-D_FORTIFY_SOURCE=2 -fstack-protector")
        # R9: -j1 — parallel make relies on the jobserver fifo, broken on HMDFS
        self.run(f'make CC="{cc}" CFLAGS="{cflags}" -j1', cwd=self.source_folder)

    def package(self):
        src = self.source_folder
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(mandir, exist_ok=True)
        # manual install: upstream `install -pDm755` is GNU-coreutils only
        exe_dst = os.path.join(bindir, "pcapfix")
        shutil.copy2(os.path.join(src, "pcapfix"), exe_dst)
        os.chmod(exe_dst, 0o755)
        shutil.copy2(os.path.join(src, "pcapfix.1"),
                     os.path.join(mandir, "pcapfix.1"))
        copy(self, "COPYING", src=src,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # pcapfix is a CLI tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
