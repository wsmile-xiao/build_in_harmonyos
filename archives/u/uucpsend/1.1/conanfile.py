#!/usr/bin/env python3
"""Conan recipe for uucpsend 1.1 — alternative UUCP batching frontend for INN.

uucpsend is the drop-in replacement for INN's ``send-uucp`` script: it reads a
per-site control file, asks INN's ``ctlinnd`` to flush the site's outgoing
batch, folds in any leftovers from the previous run, checks the free space on
the UUCP spool, and finally drives INN's ``batcher`` with a ``uux -gd ...!rnews``
command so the resulting batches are queued for the UUCP transport.

Upstream is a hand-written POSIX Makefile over two C files
(``uucpsend.c`` + ``log.c``); there is no configure, no CMake, no meson and no
test suite of any kind.

Adaptation notes (HarmonyOS PC, aarch64)
----------------------------------------
* W0 — no link-time third-party dependency: the program uses only libc
  (``stdio``/``stdlib``/``unistd``/``string``/``sys/stat``).  Its INN and
  UUCP coupling is entirely by *subprocess*: the absolute paths in
  ``paths.h`` (``ctlinnd``, ``batcher``, ``uux``, ``df``, ``du``, ``sort``,
  ``mv``, ``cat``, ``rm``) are ``system(3)``/``popen(3)`` targets, never
  linked symbols.  It therefore builds and packages standalone; the runtime
  prerequisites are documented in reports/ and manifest.yaml instead of being
  modelled as a hard ``requires()``.  See ``notes.md`` for the dependency
  status of ``uucp/1.07`` and ``inn2/2.7.4``.
* Build system — plain POSIX Makefile.  Per R33 the compiler is taken from
  ``tools.build:compiler_executables`` in the Conan profile rather than from a
  shell ``CC``, and it is handed to make as a command-line variable.  The
  recipe deliberately does not rely on the generated ``conanbuild`` env
  script: on the HarmonyOS device, running ``make`` with that script sourced
  dies with SIGSEGV, even though the same variables exported individually work
  (see manifest.yaml and reports/device-build.md).
* Three upstream portability problems are fixed by patches, not by build flags:
  ``<malloc.h>`` (a glibc/BSD extension musl does not ship), ``index()``
  (the BSD alias of ``strchr()``, removed in POSIX.1-2008), and an illegal
  lvalue cast in ``free_sites()`` that clang rejects as a hard error, making
  the unpatched source uncompilable on OHOS.
* ``make install`` is driven with ``DESTDIR`` into a staging tree and the
  payload is then copied into the package, so a recipe-owned tree is never
  written into the host ``/etc`` and no ownership change is attempted.

License: GPL-2.0-or-later.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    mkdir,
)
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc


class UucpsendConan(ConanFile):
    name = "uucpsend"
    version = "1.1"
    description = (
        "Alternative frontend for UUCP batching with INN: per-site news batch "
        "control driving ctlinnd/batcher/uux"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://www.infodrom.org/projects/uucpsend/"
    url = "https://www.infodrom.org/projects/uucpsend/"
    topics = ("uucp", "inn", "usenet", "nntp", "news", "batching", "cli")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "conandata.yml", "patches/*"

    # Produced by `make all`.
    PROGRAM = "uucpsend"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Nothing to link against.  uucpsend reaches INN and UUCP through
        # system()/popen() only -- see the module docstring.
        pass

    def validate(self):
        # POSIX-only source: getopt(3), popen(3), unistd.h, sys/stat.h and a
        # /bin/sh-driven Makefile.  R32: OHOS must be listed alongside Linux.
        if is_msvc(self) or self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "uucpsend requires a POSIX host (Linux or OHOS)"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_executable(self, key, default):
        """R33: resolve the compiler from the Conan profile, not from shell env."""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get(key) or default

    def _make_program(self):
        """Resolve make the same way Conan's Autotools helper does.

        Autotools() itself is deliberately not used: it loads make_args from
        conanbuild.conf, which only AutotoolsToolchain writes, and this project
        has no configure script for a toolchain to describe.
        """
        make_program = self.conf.get(
            "tools.gnu:make_program",
            default="mingw32-make" if self.settings_build.os == "Windows" else "make",
        )
        return make_program

    def _run_make(self, target, extra_args=(), env=None):
        """Run make in the source folder, where the Makefile and sources live.

        `env=None` means no conanbuild env script is applied; see generate().

        Note on the working directory: basic_layout() puts build_folder at
        ``<build>/<build_type>`` while source_folder is the tree that
        apply_conandata_patches() edits and that holds the Makefile.  This
        Makefile builds in-tree, so make must run in source_folder -- running it
        in build_folder fails with "No rule to make target 'all'".
        """
        command = " ".join(
            [self._make_program(), target] + [str(a) for a in extra_args]
        )
        if env is None:
            self.run(command, cwd=self.source_folder)
        else:
            self.run(command, cwd=self.source_folder, env=env)

    def generate(self):
        # R33: the compiler comes from tools.build:compiler_executables in the
        # profile, never from a shell variable, and it is passed to make as a
        # command-line variable (which also wins over the Makefile's `CC ?=`).
        #
        # Why the compiler is not left to the generated "conanbuild" env script
        # on this platform: on the HarmonyOS device, running `make` after
        # sourcing that script dies with SIGSEGV, while `make` with the same
        # variables exported individually is fine and `make` with no env at all
        # is fine (see reports/device-build.md).  Because the recipe happens to
        # have exactly one toolchain variable that matters, passing it on the
        # make command line is both the simplest and the most robust form, and
        # it removes the dependency on the env script entirely.  This mirrors
        # what other Makefile-based recipes in this repository do.
        cc = self._compiler_executable("c", "clang")
        self.output.info("resolved toolchain: CC={}".format(cc))

    def _toolchain_make_args(self):
        cc = self._compiler_executable("c", "clang")
        # -O2/-g come from the profile's build_type; -fPIE/-fstack-protector
        # and the linker hardening are the L4 baseline for a packaged binary.
        # -std=gnu89 keeps the K&R-style function definitions in uucpsend.c
        # quiet on a modern clang, which is what the source is written in.
        cflags = "-O2 -g -Wall -fPIE -fstack-protector-strong -std=gnu89"
        ldflags = "-pie -Wl,-z,relro,-z,now"
        args = [
            'CC="{}"'.format(cc),
            'CFLAGS="{}"'.format(cflags),
            'LDFLAGS="{}"'.format(ldflags),
        ]
        if self.settings.build_type in ("Debug", "RelWithDebInfo"):
            args.append("DEBUG=1")
        return args

    def build(self):
        apply_conandata_patches(self)

        # env=None: no conanbuild env script is applied (see generate()).
        self._run_make("all", ["-j1"] + self._toolchain_make_args(), env=None)

        program = os.path.join(self.source_folder, self.PROGRAM)
        if not os.path.exists(program):
            raise ConanException(
                "uucpsend build did not produce the expected program: {}".format(
                    program
                )
            )
        self.output.info("built {} ({} bytes)".format(program, os.path.getsize(program)))

        # Upstream ships no test suite at all: the Makefile defines only
        # `all`, `clean` and `install`, so there is no `check`/`test` target to
        # drive.  The runnable behaviour that can be asserted without an
        # INN/UUCP deployment lives in test_package/ instead.
        self.output.info(
            "upstream has no automated test suite (no check/test target); "
            "consumer-level assertions are in test_package/test_uucpsend.sh"
        )

    def package(self):
        # Stage inside the source tree: that is where the in-tree Makefile
        # builds, and where `make install` expects to be run from.
        stage = os.path.join(self.source_folder, "stage")
        shutil.rmtree(stage, ignore_errors=True)
        mkdir(self, stage)

        # Drive the (patched) upstream install rule into a staging tree.
        # BINDIR/CONFDIR/MANDIR keep their upstream locations inside the
        # staging root, so nothing touches the host filesystem.
        # env=None for the same reason as build(): no conanbuild script here.
        # The binary is already built, so CC is irrelevant for this step.
        self._run_make("install", ["DESTDIR={}".format(stage), "STRIP="], env=None)

        bindir = os.path.join(self.package_folder, "bin")
        licdir = os.path.join(self.package_folder, "licenses")
        docdir = os.path.join(self.package_folder, "share", "doc", "uucpsend")
        mandir8 = os.path.join(self.package_folder, "share", "man", "man8")
        mandir5 = os.path.join(self.package_folder, "share", "man", "man5")
        sample = os.path.join(self.package_folder, "share", "uucpsend")
        for directory in (bindir, licdir, docdir, mandir8, mandir5, sample):
            mkdir(self, directory)

        copy(
            self,
            self.PROGRAM,
            src=os.path.join(stage, "usr", "lib", "news", "bin"),
            dst=bindir,
            keep_path=False,
        )
        copy(
            self,
            "uucpsend.8",
            src=os.path.join(stage, "usr", "man", "man8"),
            dst=mandir8,
            keep_path=False,
        )
        copy(
            self,
            "uucpsend.ctl.5",
            src=os.path.join(stage, "usr", "man", "man5"),
            dst=mandir5,
            keep_path=False,
        )

        # The upstream install rule writes uucpsend.ctl to /etc/news.  A
        # package must not own /etc, so it is shipped as a reference
        # configuration instead; the program's *default* control path is
        # compiled in as /etc/news/uucpsend.ctl (paths.h) and is overridden
        # at run time with -c.
        copy(
            self,
            "uucpsend.ctl",
            src=os.path.join(stage, "etc", "news"),
            dst=sample,
            keep_path=False,
        )
        copy(self, "readme", src=self.source_folder, dst=docdir, keep_path=False)
        copy(self, "ChangeLog", src=self.source_folder, dst=docdir, keep_path=False)
        copy(self, "COPYING", src=self.source_folder, dst=licdir, keep_path=False)

        os.chmod(os.path.join(bindir, self.PROGRAM), 0o755)

        # G4 sanity: refuse to emit a package whose only payload is metadata.
        if not os.path.exists(os.path.join(bindir, self.PROGRAM)):
            raise ConanException(
                "uucpsend package is missing bin/{}".format(self.PROGRAM)
            )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.append_path("PATH", bindir)
        self.runenv_info.append_path("PATH", bindir)
