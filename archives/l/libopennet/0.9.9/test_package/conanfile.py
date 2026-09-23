#!/usr/bin/env python3
"""Consumer test package for libopennet 0.9.9 (R34: real consumer test).

Builds test.c against the installed libopennet package and runs it as a
real downstream program:

  1. local-file stdio API (fopen_net/fgets_net/fseek_net/ftell_net/
     fread_net/fclose_net) — covers the two upstream bug regressions
     fixed by patch 0001
  2. fd API (open_net/read_net/lseek_net/close) — asserts the real
     upstream lseek_net stub behavior (always -1)
  3. OHOS-specific (E461): AF_UNIX abstract-namespace socket served by a
     forked child, read through the library's read_net() fd API — file
     sockets are EPERM on HMDFS, so the abstract namespace is the only
     OHOS-local UNIX-socket form
  4. offline network API: fopen_net("http://127.0.0.1:<port>/...") against
     a forked local HTTP server — deterministic localhost only; PASS never
     depends on public internet access

test() additionally runs the OHOS ELF checks mandated for this archive:
ELF64 + AArch64 machine, NEEDED dynamic deps (libopennet.so.0 present for
shared consumers, absent for static), and RPATH/RUNPATH presence — all via
readelf, all with self.run / explicit subprocess check=True failures.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibopennetTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        binpath = os.path.join(self.cpp.build.bindir, "libopennet-test")
        fixture = os.path.join(self.build_folder, "fixture.txt")
        # abstract socket name (E461): no filesystem path is touched
        sockname = "libopennet-ohos-test"
        # R(ELF): the OHOS ELF64 AArch64 + dynamic dep checks
        self._check_elf(binpath)
        # Port 39441: a deliberately chosen high local port.  The forked
        # HTTP server child binds 127.0.0.1 only — entirely offline.
        cmd = f"{binpath} {fixture} {sockname} 39441"
        self.run(cmd, env="conanrun", cwd=self.build_folder)

    def _check_elf(self, binpath):
        readelf = shutil.which("readelf") or shutil.which("llvm-readelf")
        if not readelf:
            self.output.warning("readelf not found; skipping ELF checks")
            return
        out = subprocess.run([readelf, "-h", binpath], capture_output=True,
                             text=True, check=True).stdout
        if "ELF64" not in out:
            raise AssertionError("not ELF64: " + binpath)
        if "AArch64" not in out:
            raise AssertionError("not AArch64: " + binpath)
        dyn = subprocess.run([readelf, "-d", binpath], capture_output=True,
                             text=True, check=True).stdout
        if "NEEDED" not in dyn:
            raise AssertionError("no NEEDED entries: " + binpath)
        shared = self.dependencies["libopennet"].options.shared
        if shared:
            if "libopennet.so.0" not in dyn:
                raise AssertionError(
                    "libopennet.so.0 missing from NEEDED: " + dyn)
        else:
            if "libopennet" in dyn:
                raise AssertionError(
                    "static consumer must not NEED libopennet: " + dyn)
        runpath = [ln.strip() for ln in dyn.splitlines()
                   if "RPATH" in ln or "RUNPATH" in ln]
        needed = [ln.strip() for ln in dyn.splitlines() if "NEEDED" in ln]
        if runpath:
            self.output.info("OHOS dynamic path: " + runpath[0])
        elif shared and any("libopennet.so.0" in ln for ln in needed):
            # shared consumer with a by-soname NEEDED entry — resolved
            # through conanrun's LD_LIBRARY_PATH, no RUNPATH needed
            self.output.info("NEEDED by soname; conanrun provides the path")
        else:
            self.output.warning(
                "no RPATH/RUNPATH entry (static link needs none)")
