#!/usr/bin/env python3
"""Conan recipe for srf 0.1 (Sequence Read Format C++ library).

srf implements the SRF (Sequence Read Format) for DNA sequencing
data, built on top of io_lib (libstaden-read) ZTR/SRF APIs.
Static archive libsrf.a + 4 upstream test programs.

OHOS-specific adaptations (patches 0001-0003):
  - implicit-int main() in test programs (clang C++11 hard error)
  - configure secure-tmp umask 077 -> 022 (HMDFS, commoncpp2/io_lib
    precedent)
  - io_lib-config path parametrized (AC_ARG_VAR IO_LIB_CONFIG) and
    stale -lread dropped from LDLIB

Packaging notes:
  - srf's src/Makefile.am and test/Makefile.am invoke
    `io_lib-config --cflags/--libs` at BUILD time.  The io_lib package
    ships its own io_lib-config with absolute paths from ITS build
    machine, so generate() wraps it with a machine-local shim (R49:
    private prefix, never shared /usr/local).
  - Upstream ships no config.guess/sub (plain Makefile-style
    configure); AC_CANONICAL_* is absent so --build is not used.
"""
import os
import stat
import time

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain, Autotools
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class SrfConan(ConanFile):
    name = "srf"
    version = "0.1"
    description = (
        "C++ implementation of the SRF (Sequence Read Format) for "
        "DNA sequencing data, built on io_lib"
    )
    license = "GPL-2.0-or-later"
    homepage = "http://srf.sourceforge.net/"

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R36: io_lib/1.14.9 published to ohpcd (PR #14040 chain)
        self.requires("io_lib/1.14.9")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R49: private prefix under build_folder — never shared /usr/local
        prefix = os.path.join(self.build_folder, "prefix")
        tc.configure_args.append(f"--prefix={prefix}")

        # Upstream Makefiles invoke `$(SHELL io_lib-config --cflags/--libs)`,
        # but `$(SHELL ...)` is not a GNU make function — it expands to
        # EMPTY, so the io_lib flags never reach the compiler (upstream
        # only ever built with io_lib under /usr).  Parametrizing the
        # script (patch 0003) cannot fix that, so inject the io_lib flags
        # through the build env channel (CPPFLAGS/LDFLAGS) instead — the
        # same proven path io_lib uses (its -I flags land in the compile
        # line via conanbuild env).
        incdirs, libdirs = [], []
        for dep in self.dependencies.values():
            if not dep or not dep.cpp_info:
                continue
            for d in dep.cpp_info.includedirs:
                if d and str(d) not in incdirs:
                    incdirs.append(str(d))
            for d in dep.cpp_info.libdirs:
                if d and str(d) not in libdirs:
                    libdirs.append(str(d))
        env = Environment()
        for d in incdirs:
            env.append("CPPFLAGS", f"-I{d}")
        for d in libdirs:
            env.append("LDFLAGS", f"-L{d}")
        # upstream LDLIB ends with the stale 2008 name -lread; the real
        # library is libstaden-read (io_lib-config --libs spells it out)
        env.append("LDFLAGS", "-lstaden-read")
        # runtime env: find libstaden-read.so + its deps when running
        # the upstream test programs
        for d in libdirs:
            env.prepend_path("LD_LIBRARY_PATH", d)
        env.vars(self).save_script("srf_io_lib_env")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Maintainer-mode suppression: patched configure.in / Makefile.am
        # are newer than the pregenerated aclocal.m4 / Makefile.in, so
        # make tries to re-run aclocal-1.10/automake (absent on OHOS CI).
        # Refresh mtimes in autotools dependency order — every input must
        # be OLDER than its generator, and all in the past so configure's
        # sanity check (`ls -t configure` vs a fresh conftest) passes.
        src = self.source_folder
        now = time.time()
        # (file, age-seconds): larger = older
        order = (
            ("configure.in", 500),       # oldest: input of everything
            ("acinclude.m4", 500),
            ("aclocal.m4", 400),         # from configure.in+acinclude
            ("configure", 300),          # from configure.in+aclocal.m4
            ("srf_config.h.in", 250),
            # patched .am files: older than their .in generators
            ("Makefile.am", 200),
            ("src/Makefile.am", 200),
            ("test/Makefile.am", 200),
            ("Makefile.in", 100),        # newest in each .am->.in pair
            ("src/Makefile.in", 100),
            ("test/Makefile.in", 100),
        )
        for f, age in order:
            p = os.path.join(src, f)
            if os.path.exists(p):
                ts = now - age
                os.utime(p, (ts, ts))
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def _run_upstream_tests(self):
        # Upstream "tests" are 4 consumer programs writing/reading SRF
        # files with test.fastq/shortTest.fastq inputs (tests/ dir).
        # Run them against their sample data; logs to files (no pipes).
        test_env = Environment()
        iolib = self.dependencies["io_lib"]
        for d in iolib.cpp_info.libdirs:
            if d:
                test_env.prepend_path("LD_LIBRARY_PATH", str(d))
        for d in iolib.cpp_info.sysdeps:
            if d:
                test_env.prepend_path("LD_LIBRARY_PATH", str(d))
        test_env.prepend_path("LD_LIBRARY_PATH",
                              os.path.join(self.build_folder, "src"))
        test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with test_env.vars(self).apply():
            src_tests = os.path.join(self.source_folder, "test")
            outdir = os.path.join(self.build_folder, "test.out")
            os.makedirs(outdir, exist_ok=True)
            progs = ["testRead", "testWrite", "testWriteFastaq",
                     "testWriteSFF"]
            for prog in progs:
                exe = os.path.join(self.build_folder, "test", prog)
                if prog == "testRead":
                    # needs an SRF file: produce one with testWrite first
                    srf_file = os.path.join(outdir, "written.srf")
                    if not os.path.exists(srf_file):
                        self.run('"%s" "%s" > "%s/write.log" 2>&1'
                                 % (os.path.join(self.build_folder,
                                                 "test", "testWrite"),
                                    os.path.join(src_tests,
                                                 "shortTest.fastq"),
                                    outdir))
                self.run('"%s" "%s" > "%s/%s.log" 2>&1'
                         % (exe, srf_file if prog == "testRead"
                            else os.path.join(src_tests, "shortTest.fastq"),
                            outdir, prog))

    def package(self):
        # plain `make install` into the private prefix, then copy
        # (autotools.install() DESTDIR nesting pitfall, io_lib precedent)
        autotools = Autotools(self)
        autotools.make(target="install")
        src_prefix = os.path.join(self.build_folder, "prefix")
        copy(self, "*", src_prefix, self.package_folder)
        # upstream installs no headers (src/Makefile.am only declares
        # lib_LIBRARIES) — ship the public .hh interface for consumers
        copy(self, "*.hh", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["srf"]
        self.cpp_info.includedirs = ["include"]
        # upstream test programs are the de-facto CLI for inspecting SRF
        self.cpp_info.bindirs = ["bin"]
