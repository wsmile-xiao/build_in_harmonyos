#!/usr/bin/env python3
"""Conan recipe for paxtest 0.9.15 — PaX/GrSecurity memory-protection regression suite.

paxtest probes the process-memory protection of a running kernel: it tries to
execute code planted in every writable memory class (anonymous mapping, bss,
data, heap, stack, shared-library bss/data), tries mprotect()-based variants,
tries to overwrite text segments, runs return-to-function attacks, and measures
the quality (bits) of address-space randomization of mappings, heap, main
executable, shared libraries, vDSO, stack and argv/env.

OHOS adaptation notes (HarmonyOS PC, aarch64):

* Build: upstream `make linux` -> `make -f Makefile.psm`, whose probes are
  x86-oriented and hardcode `CC := gcc` / `LD := ld`.  The OHOS SDK clang is
  passed through `make CC=<clang> LD=<ld>` from the Conan conf (R33); on
  aarch64 THEARCH stays empty and the -m32/-m64/-msecure-plt/-ftrampolines
  probes simply do not match, so no x86-only flags survive.
* Patches 0001-0004 (portability): chpax-0.7 drops its dead a.out (pre-ELF)
  support because musl-based sysroots ship no <a.out.h>; a.out does not exist
  on aarch64 anyway.  chpax itself is inert on OHOS (the kernel has no PaX
  flags to set, and upstream's ELF machine list has no EM_AARCH64), so the
  generated paxbin wrapper is a harmless no-op; the suite's default-path
  behaviour is unaffected.
* Patch 0005 (portability): shellcode.h gains the missing __aarch64__ branch
  (ARM64 `ret`, 0xd65f03c0) so the exec tests keep their positive signal; the
  upstream fallback is an x86 RET byte which cannot distinguish an executable
  page from a non-executable one on ARM64 (both end as a signal death).
* Blackhat mode: upstream body.c uses a GCC nested-function trampoline; when
  built with clang, `paxtest blackhat` prints
  "INFO: The blackhat mode not supported due to missing nested function
  support in clang." and continues with kiddie semantics (upstream limitation,
  see reports/test-report.md).
* package(): ships the complete built run directory under bin/paxtest.  The
  driver resolves the test programs relative to the current directory and sets
  LD_LIBRARY_PATH itself, so consumers run it from that directory:
  `cd <pkg>/bin/paxtest && ./paxtest kiddie [logfile]`.
* License: GPL-2.0-or-later (upstream COPYING; README says "version 2 or later").
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

TEST_PROGRAMS = [
    "anonmap", "execbss", "execdata", "execheap", "execstack",
    "shlibbss", "shlibdata",
    "mprotanon", "mprotbss", "mprotdata", "mprotheap", "mprotstack",
    "mprotshbss", "mprotshdata", "writetext",
    "randamap", "randheap1", "randheap2", "randmain1", "randmain2",
    "randshlib", "randvdso", "randstack1", "randstack2", "randarg1", "randarg2",
    "randshlibdelta1", "randshlibdelta2", "randexhaust1", "randexhaust2",
    "rettofunc1", "rettofunc2", "rettofunc1x", "rettofunc2x",
]

UTILITIES = [
    "getamap",
    "getheap1", "getheap2", "getmain1", "getmain2",
    "getshlib", "getvdso", "getstack1", "getstack2",
    "getarg1", "getarg2", "getexhaust1", "getexhaust2",
    "getshlibdelta1", "getshlibdelta2",
]


class PaxtestConan(ConanFile):
    name = "paxtest"
    version = "0.9.15"
    description = (
        "PaX/GrSecurity memory-protection regression suite: executable "
        "mapping/mprotect/writetext probes and address-space randomization "
        "quality measurement"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/opensrcsec/paxtest"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("security", "memory-protection", "pax", "aslr", "regression")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "paxtest targets POSIX kernels (mmap/mprotect/ELF shellcode "
                "probes); got {0}".format(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        ld = compilers.get("ld", "ld")
        # R9: -j1.  R33: compiler/linker from Conan conf, passed on the make
        # command line (upstream Makefile.psm hardcodes CC/LD).
        self.run(
            'make -j1 -f Makefile.psm CC="{0}" LD="{1}"'.format(cc, ld),
            cwd=self.source_folder,
        )

    def package(self):
        dst = os.path.join(self.package_folder, "bin", "paxtest")
        copy(
            self,
            "*",
            src=self.source_folder,
            dst=dst,
            excludes=("*.o", "debian/*", ".edit-tracker.json", ".tarball-sha256"),
        )
        for name in ["paxtest", "chpax", "paxbin", "genpaxtest"] + TEST_PROGRAMS + UTILITIES:
            path = os.path.join(dst, name)
            if os.path.isfile(path):
                os.chmod(path, 0o755)
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin", "paxtest")
        )
