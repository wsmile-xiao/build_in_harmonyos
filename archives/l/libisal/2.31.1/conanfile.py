#!/usr/bin/env python3
"""Conan recipe — libisal 2.31.1 (Intel ISA-L, upstream Makefile.unx).

ISA-L is Intel's Intelligent Storage Acceleration Library: CRC16/32/64,
igzip raw-deflate/gzip compression, RAID XOR/PQ generate+check and GF(2^8)
erasure coding.  On aarch64 upstream ships NEON / SVE / CRC-extension
implementations for every module (crc, erasure_code, raid, igzip, mem),
selected at runtime through a self-patching multibinary trampoline driven
by getauxval(AT_HWCAP) — plain code, no ifunc, OHOS friendly.  With no hw
feature bits the dispatcher falls back to the portable base C routines,
so the library stays correct on any aarch64 CPU.

Build strategy: the official v2.31.1 source archive ships no configure
(release has no dist asset), so instead of bootstrapping autotools with
tool_requires (automake/autoconf/libtool cannot be built on HMDFS — their
own configure scripts hit the exec-permission wall), the recipe uses the
upstream-maintained hand-written `Makefile.unx` + `make.inc` build system.
It includes the very same per-module Makefile.am source lists, picks the
aarch64 sources via host_cpu, sets `AS=$(CC) -D__ASSEMBLY__` for the .S
files, builds bin/isa-l.a + the igzip CLI and can build/run the upstream
check suite (`make check`, 16 tests).

OHOS adaptation points:
1. `arch=aarch64 host_cpu=aarch64` passed explicitly — make.inc's uname
   heuristics would derive arch="HarmonyOS" on OHOS.
2. All 52 aarch64 .S files (`.req` register aliases included) assemble
   fine with clang 15's integrated assembler — verified by the full
   upstream `make check` 16/16 pass on an OHOS device (no -fno-integrated-as
   needed, unlike the sibling isa-l_crypto 2.26 whose SVE tables trip the
   integrated assembler).
3. AR passed from Conan conf (llvm-ar); the lib target then archives with
   `ar cr` semantics.
4. TMPDIR redirected into the build folder (OHOS /tmp is read-only;
   make.inc's assembler-feature and pthread probes call mktemp).
5. `make check` runs the 16 upstream check tests (crc 4, erasure_code 4,
   igzip 3, mem 1, raid 4); packaging is done by explicit copies so no
   `make install` symlinks/man pages are involved.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibisalConan(ConanFile):
    name = "libisal"
    version = "2.31.1"
    description = (
        "Intel Intelligent Storage Acceleration Library: CRC16/32/64, igzip "
        "deflate/gzip compression, RAID XOR/PQ and GF(2^8) erasure coding "
        "with aarch64 NEON/SVE/CRC-ext accelerated implementations"
    )
    license = "BSD-3-Clause"
    homepage = "https://github.com/intel/isa-l"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"
    # Static-only: the `slib` target needs a .so symlink chain that HMDFS
    # may reject, and static matches how CI consumers link -lisal.

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libisal supports Linux/OHOS only")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _make_base(self):
        # R33: compiler/tools come from Conan conf, never from the shell.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = executables.get("c", "clang")
        ar = executables.get("ar", "llvm-ar")
        # CC is `?=` in make.inc and AS/LINK.o derive from it, so passing
        # CC/AR on the command line reaches every rule without clobbering
        # make.inc's own `CFLAGS =` assignment.
        return (f'make -f Makefile.unx arch=aarch64 host_cpu=aarch64 '
                f'version={self.version} CC="{cc}" AR={ar}')

    def build(self):
        apply_conandata_patches(self)
        # OHOS /tmp is read-only; make.inc's probes call mktemp.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

        base = self._make_base()
        # Static lib (bin/isa-l.a) + igzip CLI; the `slib` shared target is
        # skipped (symlink chain, and the static default is what CI tests).
        self.run(f"{base} lib progs", cwd=self.source_folder, env="conanbuild")
        # Upstream check suite: builds the 16 check tests and runs them.
        self.run(f"{base} check", cwd=self.source_folder, env="conanbuild")

    def package(self):
        lib = os.path.join(self.package_folder, "lib")
        inc = os.path.join(self.package_folder, "include")
        src = self.source_folder
        copy(self, "isa-l.a", src=os.path.join(src, "bin"), dst=lib,
             keep_path=False)
        os.rename(os.path.join(lib, "isa-l.a"), os.path.join(lib, "libisal.a"))
        # Public headers install as include/isa-l/*.h + include/isa-l.h so
        # consumers use #include <isa-l/crc.h> (same layout as autotools).
        copy(self, "*.h", src=os.path.join(src, "include"),
             dst=os.path.join(inc, "isa-l"), keep_path=False)
        copy(self, "isa-l.h", src=src, dst=inc, keep_path=False)
        # igzip is built by the `progs` target at programs/igzip (bin/ only
        # holds the .o files and the archive).
        copy(self, "igzip", src=os.path.join(src, "programs"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["isal"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]  # igzip CLI
        self.cpp_info.set_property("cmake_file_name", "libisal")
        self.cpp_info.set_property("cmake_target_name", "libisal::isal")
        self.cpp_info.set_property("pkg_config_name", "libisal")
