#!/usr/bin/env python3
"""Conan recipe for libpfm4 — HarmonyOS PC (aarch64).

libpfm4 ships a hand written Makefile hierarchy (no configure, no CMake), so
the build is driven directly.  Three make variables carry the adaptation:

  SYS=Linux     The kernel interface of HarmonyOS is the Linux one, but
                uname(1) reports "HarmonyOS" and config.mk takes SYS from
                uname.  lib/Makefile compiles the generic perf_events PMU
                (pfmlib_perf_event.c, pfmlib_perf_event_pmu.c,
                pfmlib_perf_event_raw.c) only when SYS is Linux — without it
                the library has no PERF_COUNT_* events at all.
  ARCH=aarch64  selects CONFIG_PFMLIB_ARCH_ARM64 in config.mk (ARMv8 PMU
                tables and the architecture specific tests).
  NOPYTHON=y    skips the python/SWIG sub-project (SWIG is not available).

patches/0001 and patches/0002 fix the public ABI size constants in pfmlib.h
and pfmlib_perf_event.h: upstream derived them from glibc's __WORDSIZE only,
and the musl based OHOS sysroot ships no <bits/wordsize.h>, so the constants
fell back to their 32-bit values while the structures themselves stayed
64-bit.
"""
import os

from conan import ConanFile
from conan.tools.build import build_jobs
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class Libpfm4Conan(ConanFile):
    name = "libpfm4"
    version = "4.13.0-git106-g3e4031b"
    description = "Helper library to develop monitoring tools exploiting the perf_event interface"
    license = "MIT"
    homepage = "https://github.com/wcohen/libpfm4"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # The compiler is taken from the Conan profile
        # (tools.build:compiler_executables); config.mk would otherwise use
        # whichever clang happens to be first in PATH.
        cc = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict).get("c", "clang")
        args = [
            "CC=%s" % cc,
            "SYS=Linux",
            "ARCH=aarch64",
            "NOPYTHON=y",
            "CONFIG_PFMLIB_SHARED=%s" % ("y" if self.options.shared else "n"),
        ]
        jobs = "-j%d" % build_jobs(self)
        self.run("make %s %s lib" % (jobs, " ".join(args)),
                 cwd=self.source_folder)
        # Upstream test suite (tests/Makefile: TARGETS = validate).  The test
        # binary is linked against the static libpfm.a, so it runs in place.
        tests_dir = os.path.join(self.source_folder, "tests")
        self.run("make %s %s" % (jobs, " ".join(args)), cwd=tests_dir)
        self.run("./validate", cwd=tests_dir)

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "include", "perfmon"),
             dst=os.path.join(self.package_folder, "include", "perfmon"))
        libdir = os.path.join(self.source_folder, "lib")
        dst_libdir = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            # copy the shared object itself and reproduce the soname chain
            # (libpfm.so.4, libpfm.so) built by lib/Makefile
            soname = None
            for name in os.listdir(libdir):
                path = os.path.join(libdir, name)
                if name.startswith("libpfm.so.") and not os.path.islink(path):
                    copy(self, name, src=libdir, dst=dst_libdir)
                    soname = name
            if soname:
                for link in ("libpfm.so.4", "libpfm.so"):
                    link_path = os.path.join(dst_libdir, link)
                    if not os.path.exists(link_path):
                        os.symlink(soname, link_path)
        else:
            copy(self, "libpfm.a", src=libdir, dst=dst_libdir)

    def package_info(self):
        # the artifact is libpfm.a / libpfm.so, hence -lpfm
        self.cpp_info.libs = ["pfm"]
