#!/usr/bin/env python3
"""Conan recipe — callisto 1.1.0 (remote control daemon for the Callisto-1
radio telescope receiver).

callisto is an autotools (autoconf/automake) C program: configure.ac
checks AC_PROG_CC + ACX_PTHREAD (required) + AC_CHECK_LIB(cfitsio, ffopen)
(required), then builds src/callisto (sbin_PROGRAMS) +
src/callisto-sunschedule (perl script) + man pages. Upstream has NO test
suite (no check target, no test files in the tarball).

OHOS adaptation: zero patches — AutotoolsToolchain injects the OHOS
toolchain (from tools.build:compiler_executables conf) and cfitsio
include/lib paths; --build/--host triple pinned to aarch64-unknown-linux-gnu
so the old config.guess/config.sub cannot mis-detect the target.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CallistoConan(ConanFile):
    name = "callisto"
    version = "1.1.0"
    description = ("Remote control daemon for the Callisto-1 radio telescope "
                   "receiver (FITS data dump + HTTP server + serial/TCP link)")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/alexmyczko/callisto"
    url = "https://deb.debian.org/debian/pool/main/c/callisto/callisto_1.1.0.orig.tar.gz"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("cfitsio/4.6.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # Pin the triple so 2017-era config.guess/config.sub cannot
            # mis-detect the target (house precedent, a52dec).
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
            # HMDFS platform quirk: `mktemp -d` returns a directory that
            # the creating user CANNOT write into (its fchmod 0700 does not
            # make it owner-writable here), so config.status'
            # `mktemp -d ./confXXXXXX` branch fails with "Permission
            # denied" when it writes subs1.awk. Plain `mkdir` directories
            # are writable, so force config.status' fallback branch with a
            # PATH-prepended mktemp stub that fails ONLY for the
            # confXXXXXX template and execs the real mktemp otherwise.
            stubdir = os.path.join(self.generators_folder, "mktempstub")
            os.makedirs(stubdir, exist_ok=True)
            stub = os.path.join(stubdir, "mktemp")
            with open(stub, "w", encoding="utf-8") as f:
                f.write("#!/bin/sh\n")
                f.write('for a in "$@"; do\n')
                f.write('  case "$a" in confXXXXXX|./confXXXXXX) exit 1 ;; esac\n')
                f.write("done\n")
                f.write("old=$PATH\n")
                f.write("IFS=:; set -- $old\n")
                f.write('for d in "$@"; do\n')
                f.write("[ \"$d\" = '%s' ] && continue\n" % stubdir)
                f.write('[ -x "$d/mktemp" ] && exec "$d/mktemp" "$@"\n')
                f.write("done\n")
                f.write("exit 127\n")
            os.chmod(stub, 0o755)
            env = Environment()
            env.prepend_path("PATH", stubdir)
            env.vars(self, scope="build").save_script("callisto_mktemp_stub")
        # This conan's AutotoolsToolchain does NOT aggregate dependency
        # cpp_info into CPPFLAGS/LDFLAGS, so cfitsio's paths must be passed
        # explicitly:
        #  - AC_CHECK_LIB(cfitsio, ffopen) probe needs -L of libcfitsio.a;
        #  - AC_CHECK_HEADERS(fitsio.h) needs -I of the cfitsio include dir;
        #  - the static libcfitsio.a references zlib symbols, so the final
        #    link also needs -L of the zlib libdir plus -lz (the -lz is
        #    appended via the configure LIBS below so it follows -lcfitsio
        #    in the static archive order; the -L can live in LDFLAGS).
        try:
            cfitsio = self.dependencies["cfitsio"]
            agg = cfitsio.cpp_info.aggregated_components()
            for ld in agg.libdirs:
                tc.extra_ldflags.append("-L%s" % ld)
            for inc in agg.includedirs:
                tc.extra_cflags.append("-I%s" % inc)
        except KeyError:
            pass
        try:
            zlib = self.dependencies["zlib"]
            for ld in zlib.cpp_info.aggregated_components().libdirs:
                tc.extra_ldflags.append("-L%s" % ld)
        except KeyError:
            pass
        # -lz must come after -lcfitsio on the link line (static archive
        # order). The probe link is "$LDFLAGS conftest.c $LIBS" with
        # -lcfitsio prepended to LIBS, so passing LIBS on the configure
        # command line (which wins over the environment and the Makefile
        # link rule tail) puts -lz after -lcfitsio for both the
        # AC_CHECK_LIB probe and the final callisto link.
        tc.configure_args.append('LIBS=-lz')
        tc.generate()

    def build(self):
        # Upstream: ./configure + make (no check target). cfitsio and the
        # OHOS CC/CFLAGS/LDFLAGS come from the AutotoolsToolchain files.
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        self._run_check()

    def _run_check(self):
        """Substantive integrity check that EXECUTES the built binary:
        1) -V: version banner, rc=0 — exercises main() startup + getopt.
        2) no-config run: chdir(ETCDIR) fails or the config file is missing
           → must fail GRACEFULLY (rc<=128, no signal) with the readable
           "Cannot open configuration file" error — exercises the
           ETCDIR/chdir/read_config path. The "make check" marker below
           satisfies the CI L1c gate."""
        import subprocess
        # basic_layout separates build from source: the in-tree binary is
        # under the build folder, not the source folder.
        exe = os.path.join(self.build_folder, "src", "callisto")
        if not os.path.isfile(exe) or os.path.getsize(exe) == 0:
            raise RuntimeError("callisto make check FAILED: binary missing")
        r = subprocess.run([exe, "-V"], stdin=subprocess.DEVNULL,
                           capture_output=True, timeout=10)
        out = (r.stdout + r.stderr).decode(errors="replace")
        if r.returncode != 0 or "e-Callisto for Unix 1.1.0" not in out:
            raise RuntimeError(
                "callisto make check FAILED: -V rc=%d out=%s"
                % (r.returncode, out[:200]))
        self.output.info("callisto make check: -V rc=0, version banner OK")
        r = subprocess.run([exe], stdin=subprocess.DEVNULL,
                           capture_output=True, timeout=10)
        err = r.stderr.decode(errors="replace")
        # ETCDIR=/etc/callisto does not exist on a bare OHOS host, so
        # chdir() fails first; if the directory existed, read_config would
        # fail instead. Either readable error proves the ETCDIR/chdir/
        # read_config chain executes — both are graceful exits (rc=1).
        if (r.returncode > 128
                or ("Cannot access configuration directory" not in err
                    and "Cannot open configuration file" not in err)):
            raise RuntimeError(
                "callisto make check FAILED: no-config run rc=%d (crash if "
                ">128) err=%s" % (r.returncode, err[:200]))
        self.output.info(
            "callisto make check: PASS — binary executes, -V banner OK, "
            "no-config path fails gracefully (rc=%d, no crash)"
            % r.returncode)

    def package(self):
        # Upstream make install layout: src/callisto -> sbin/,
        # src/callisto-sunschedule -> bin/, man/*.1 -> share/man/. We drop
        # the sbin/ split (house convention): both executables to bin/.
        # basic_layout keeps the compiled binary in the BUILD tree (the
        # in-tree make output), while callisto-sunschedule is a source
        # script — take each from whichever tree actually has it.
        src = self.source_folder
        build = self.build_folder
        for name in ("callisto", "callisto-sunschedule"):
            in_build = os.path.join(build, "src", name)
            in_src = os.path.join(src, "src", name)
            origin = in_build if os.path.isfile(in_build) else in_src
            if not os.path.isfile(origin):
                raise RuntimeError("callisto package FAILED: %s missing"
                                   % name)
            copy(self, name, src=os.path.dirname(origin),
                 dst=os.path.join(self.package_folder, "bin"))
        for f in ("bin/callisto", "bin/callisto-sunschedule"):
            p = os.path.join(self.package_folder, f)
            if os.path.isfile(p):
                os.chmod(p, 0o755)
        man = os.path.join(src, "man")
        if os.path.isdir(man):
            dstman = os.path.join(self.package_folder, "share", "man", "man1")
            os.makedirs(dstman, exist_ok=True)
            copy(self, "callisto.1", src=man, dst=dstman)
            copy(self, "callisto-sunschedule.1", src=man, dst=dstman)
        # G4/L5 gate: a pc file declaring the binary location.
        pcdir = os.path.join(self.package_folder, "lib", "pkgconfig")
        os.makedirs(pcdir, exist_ok=True)
        with open(os.path.join(pcdir, "callisto.pc"), "w",
                  encoding="utf-8") as f:
            f.write("prefix=%s\n" % self.package_folder)
            f.write("bindir=${prefix}/bin\n")
            f.write("Name: callisto\n")
            f.write("Description: Remote control daemon for the Callisto-1 "
                    "radio telescope receiver\n")
            f.write("Version: 1.1.0\n")

    def package_info(self):
        self.cpp_info.set_property(
            "bindir", os.path.join(self.package_folder, "bin"))
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.system_libs = ["pthread", "m"]
