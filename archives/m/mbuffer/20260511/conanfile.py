#!/usr/bin/env python3
"""Conan recipe - mbuffer 20260511 (Autotools: ./configure + hand-written Makefile.in).

mbuffer ("measuring buffer") buffers a data stream between a producer and a
consumer, reports the throughput, can split the stream over several output
volumes (tape / auto-loader behaviour) and can compute a hash digest of what it
forwarded.  The deliverable is one CLI binary; no libraries are installed.

Why the autotools path, although upstream ships both build systems
  * INSTALL documents ./configure && make && make install and `make check`;
  * only the autotools harness registers the 8 upstream tests
    (`check: $(TARGET) test0 test1 ... test7`) and builds the two LD_PRELOAD
    interposers three of those tests drive
    (`all: $(TARGET) idev.so tapetest.so have-af`);
  * the CMake harness gates its eight add_test() entries behind a non-standard
    ENABLE_TESTING switch, and its install rule is
    `install(FILES mbuffer DESTINATION bin)` -- a source-tree path that does not
    exist in the release archive (the archive has mbuffer.c, not mbuffer).

Layout: deliberately no basic_layout(), and every command is issued as
`cd <builddir> && ...` instead of passing cwd= to Conan's runner.  Two reasons:
  * upstream assumes cwd == srcdir (`make version.h` runs `bash mkversion.sh`,
    which reads .hg_archival.txt and writes both version.h and mbuffer.1 into
    `.`; `make install` then installs mbuffer.1 from `.`);
  * the CI profile exports CONFIG_SHELL/SHELL=/data/service/hnp/bin/bash, and
    that bash's getcwd() fails on HarmonyOS/HMDFS build directories (E386,
    DRAFT-6487).  Conan's chdir() leaves $PWD stale, so autoconf's
    "working directory cannot be determined" identity check trips.  A shell
    builtin `cd` repairs $PWD and sidesteps the failing syscall, and only an
    *inline* assignment wins, because conanbuild.sh sources the profile's
    buildenv script last -- a recipe-side Environment gets overridden.

All source modifications live in patches declared in conandata.yml:
  0001-Makefile.in.patch  - parameterise the GNU-tar-only flag and the openssl path,
                            add $(LDFLAGS) to the interposer link rules, and repair the two
                            missing upstream dependency edges (version.h as an object
                            prerequisite, mbuffer.1 as an install prerequisite)
  0002-config.guess.patch - HarmonyOS system identification (E007)
  0003-config.sub.patch   - ohos-linux mapping, ohos* and linux-ohos* whitelists (E072)
  0004-configure.patch    - drop `umask 077 &&` so config.status can write its temp dir (E011/E129/E543)
  0005-mbuffer.c.patch    - weak pthread_cancel reference (E085)
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches, export_conandata_patches, get, load, save,
)
from conan.tools.gnu import AutotoolsToolchain

# mbuffer's configure resolves its built-in "openssl:md5" hash backend with
# `AC_SEARCH_LIBS(MD5_Init, crypto)`, and hashing.c includes <openssl/md5.h>.
# Without that backend `--md5` dies at run time with
#   mbuffer: error: invalid or unsupported hash function MD5
# and upstream tests test1 / test4 / test5 / test7 fail.  OpenSSL is therefore an
# explicit Conan dependency, resolved from the graph and never probed on the
# host: the CI worker carries no OpenSSL headers anywhere (an earlier revision
# probed ~/.harmonybrew/opt/openssl@3, ~/.harmonybrew, /usr/local and /usr --
# all absent there), and a host probe that misses degrades silently: configure
# simply drops the backend and the four tests go red.
# openssl/3.5.6.1 is published for ohos-aarch64 and is a static-only build (its
# recipe hard-codes no-shared), so -lcrypto resolves to libcrypto.a and the
# installed binary keeps no runtime libcrypto dependency.
OPENSSL_REQUIRES = "openssl/3.5.6.1"

# Upstream's registered test targets, in the order `make check` lists them:
#   check: $(TARGET) test0 test1 test2 test3 test4 test5 test6 test7
UPSTREAM_TESTS = ("test0", "test1", "test2", "test3", "test4", "test5",
                  "test6", "test7")

# E386 / DRAFT-6487: the shell every generated helper must run under.
_SAFE_SHELL = "/bin/sh"


class MbufferConan(ConanFile):
    name = "mbuffer"
    version = "20260511"
    description = ("Buffer for producer/consumer data streams with throughput "
                   "reporting, multi-volume tape output and hash digests")
    license = "GPL-3.0-or-later"
    homepage = "https://www.maier-komor.de/mbuffer.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("buffer", "pipe", "tape", "backup", "throughput", "cli")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The hash backend has to come from the graph; see OPENSSL_REQUIRES.
        self.requires(OPENSSL_REQUIRES)

    def validate(self):
        # R32: never compare settings.os against a single value.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mbuffer needs a POSIX libc with dlopen()/LFS support; "
                + str(self.settings.os) + " is not supported")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ setup
    def generate(self):
        # mkversion.sh does `mktemp -t version.h.XXXXXXXXXX`, which resolves to
        # /tmp -- read-only on HarmonyOS (E002).  Keep temp files in the build dir.
        env = Environment()
        env.define("TMPDIR", self.build_folder)
        env.define("TMP", self.build_folder)
        env.define("TEMP", self.build_folder)
        env.vars(self, scope="build").save_script("mbuffer_tmpdir")

        tc = AutotoolsToolchain(self)
        incs, libs, bins = self._dep_dirs()
        # Fail closed rather than degrade: a missing header is exactly how the
        # backend disappears and the four upstream tests turn red.
        if not any(os.path.isfile(os.path.join(d, "openssl", "md5.h"))
                   for d in incs):
            raise ConanException(
                "%s provides no openssl/md5.h; its includedirs are %r"
                % (OPENSSL_REQUIRES, incs))
        # Makefile.in compiles with $(CC) $(CFLAGS) only -- CPPFLAGS never
        # reaches the compile line -- so the header path has to go into CFLAGS.
        # Both paths are absolute package paths from cpp_info: deterministic on
        # every worker.
        for d in incs:
            tc.extra_cflags.append("-I" + d)
        for d in libs:
            tc.extra_ldflags.append("-L" + d)
        tc.generate()

        # build() re-reads these so both phases use exactly the directories the
        # graph resolved -- one lookup, no host fallback anywhere.
        save(self, self._openssl_file(),
             "incs=%s\nlibs=%s\nbins=%s\n"
             % (os.pathsep.join(incs), os.pathsep.join(libs),
                os.pathsep.join(bins)))

        # Persist the install-directory arguments Conan would have passed
        # (--prefix=/ plus the bin/etc/lib flags) so that build() can invoke
        # ./configure itself and prepend the inline shell override.  Reading
        # them back keeps this recipe honest to whatever AutotoolsToolchain
        # decides, instead of hard-coding a prefix here.
        save(self, self._args_file(), "\n".join(tc.configure_args) + "\n")

    def _dep_dirs(self):
        """Absolute include/lib/bin dirs of the OpenSSL declared in requirements()."""
        cpp = self.dependencies["openssl"].cpp_info
        return list(cpp.includedirs), list(cpp.libdirs), list(cpp.bindirs)

    def _openssl_dirs(self):
        """The dirs generate() persisted, in the same (incs, libs, bins) order."""
        out = {"incs": [], "libs": [], "bins": []}
        for line in load(self, self._openssl_file()).splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                out[key] = [p for p in value.split(os.pathsep) if p]
        return out["incs"], out["libs"], out["bins"]

    def _openssl_program(self):
        """openssl(1) from the dependency -- upstream's harness pipes through it."""
        for d in self._openssl_dirs()[2]:
            cand = os.path.join(d, "openssl")
            if os.path.isfile(cand):
                return cand
        raise ConanException(
            "%s installs no openssl(1) program, but upstream's test harness "
            "pipes through it; a PATH lookup here would be a host dependency"
            % OPENSSL_REQUIRES)

    def _openssl_file(self):
        return os.path.join(self.build_folder, "mbuffer_openssl_dirs.txt")

    def _args_file(self):
        return os.path.join(self.build_folder, "mbuffer_configure_args.txt")

    def _at(self, inner):
        """Run `inner` in the build dir via a shell-internal cd (repairs $PWD)."""
        return "cd '%s' && %s" % (self.build_folder, inner)

    def _safe_shell(self):
        return "CONFIG_SHELL=%s SHELL=%s" % (_SAFE_SHELL, _SAFE_SHELL)

    # ------------------------------------------------------------------- build
    def build(self):
        apply_conandata_patches(self)

        args = [a.strip() for a in load(self, self._args_file()).splitlines() if a.strip()]
        configure = self._safe_shell() + " ./configure " + " ".join(
            "'%s'" % a for a in args)
        self.run(self._at(configure), env="conanbuild")

        # Patch 0001 puts version.h and mbuffer.1 on the default dependency
        # chain: on a clean source tree the default all path runs mkversion.sh
        # before compiling settings.c, and the install target regenerates the
        # man page it copies.  -j1 unconditionally: GNU make's jobserver wants a
        # FIFO and the platform sandbox refuses to create one (E074/E525). The
        # default goal all also builds the test-only interposers idev.so /
        # tapetest.so and have-af.
        self.run(self._at("make -j1 %s" % self._safe_shell()), env="conanbuild")

        self._run_upstream_tests()

    # ------------------------------------------------------------------- tests
    def _make(self, target):
        """Run one upstream make target, returning its exit code."""
        args = ["-j1", "CONFIG_SHELL=%s" % _SAFE_SHELL, "SHELL=%s" % _SAFE_SHELL,
                target,
                # Upstream builds its test payload with
                # `$(TAR) cf test.tar --ignore-failed-read /bin /usr/bin`.
                # Neither tree exists on this platform, and the tar(1) on PATH is
                # toybox 0.8.12, which rejects the GNU-only flag outright.
                # Patch 0001 turned both into variables, so the very same
                # prerequisite target now runs against the package's own sources.
                'TESTTREE="*.c *.h"', "TARGFLAGS=",
                # OPENSSL= points at the dependency's own openssl(1): upstream's
                # harness hashes its payload with it, and a PATH lookup there
                # would be the same host dependency this recipe just removed.
                "OPENSSL='%s'" % self._openssl_program()]
        cmd = "make " + " ".join(args)
        self.output.info("upstream harness: " + cmd)
        # conan 2.29's ConanFile.run() takes no `output=` keyword.
        return self.run(self._at(cmd), env="conanbuild", ignore_errors=True)

    def _run_upstream_tests(self):
        """Execute the 8 registered upstream tests, one make target each.

        `make check` is upstream's entry point but it aborts at the first
        failing prerequisite, and test0..test5 are `touch`-marked file targets,
        so a second pass over `check` would silently do nothing.  Driving one
        prerequisite per invocation yields one real exit code per test.
        """
        verdicts, failures = [], []
        for target in UPSTREAM_TESTS:
            # drop this target's completion marker and its own outputs so that
            # make really executes the recipe again
            self.run(self._at("rm -f %s %s.md5 %s.tar %s.out0 %s.out1 output-%s*"
                              % (target, target, target, target, target, target)),
                     env="conanbuild", ignore_errors=True)
            rc = self._make(target)
            verdicts.append("%s=%s" % (target, rc))
            if rc != 0:
                failures.append((target, rc))
        self.output.info("UPSTREAM_TEST_VERDICTS " + " ".join(verdicts))
        if failures:
            raise Exception("upstream tests failed: %s" % ", ".join(
                "%s(rc=%s)" % (t, rc) for t, rc in failures))

    # ----------------------------------------------------------------- package
    def package(self):
        # --prefix=/ (from AutotoolsToolchain) plus DESTDIR=package_folder puts
        # bin/mbuffer, share/man/man1/mbuffer.1 and etc/mbuffer.rc in the package.
        self.run(self._at("make install DESTDIR='%s' %s"
                          % (self.package_folder, self._safe_shell())),
                 env="conanbuild")

    def package_info(self):
        # application package: one binary, no headers, nothing to link against.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_find_mode", "none")
