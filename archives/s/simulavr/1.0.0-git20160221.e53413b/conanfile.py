#!/usr/bin/env python3
"""Conan recipe — simulavr 1.0.0-git20160221.e53413b

simulavr is an AVR microcontroller simulator: it builds the ``libsim``
simulation library (using the bundled ElfIO to read AVR firmware) plus the
``simulavr`` command-line simulator, which can also act as a GDB remote
server.  Adapted here for HarmonyOS PC (OHOS / aarch64), native build.

Adaptation scope (W0-W5; device shadow-CI results in notes.md):
- autotools + libtool project whose pristine orig tree ships only the autotools
  *inputs* (configure.ac / Makefile.am / m4/) — no generated configure,
  config.guess/sub, ltmain.sh, src/config.h.in or Makefile.in.  Upstream builds
  them with ./bootstrap.  On the HarmonyOS build host that bootstrap cannot run
  (autoreconf lives off-PATH in /data/service/hnp/bin, automake/aclocal/libtoolize
  are absent from the device and the cached copies are mode 750 owned by another
  uid; HMDFS denies execve of the job user's own files).  So the generated
  build system is committed under ``preconf/`` (produced by ``autoreconf -fi``
  in a clean Debian container) and copied over the source tree in source();
  ``preconf/README.md`` documents provenance.  This mirrors the repo's
  agg / libagg / afflib "preconf"/"generated" idiom.
- the package is delivered as the ``simulavr`` CLI (``package_type =
  "application"``).  libsim is built as an automake *convenience library* and
  linked into the executable: the AVR device models self-register at
  static-init time via ``AVR_REGISTER`` and ``main`` never references them, so
  a normal archive would drop every registrar and ``simulavr -d atmega128``
  would fail with "Invalid device specification" (upstream avoids this by
  shipping libsim as a *shared* library).  See ``preconf/README.md``; no
  ``Makefile.am`` patch is shipped on purpose, so that nothing can trigger an
  ``automake`` regeneration the build host cannot run.
- Upstream regression suite: ``regress/`` holds 78 test_opcodes modules that
  expand to 14706 generated test cases (verified locally: 78/78 modules,
  14706 classes, 0 errors).  They are driven by ``make check`` ->
  ``regress/regress.py``, which launches the freshly built ``src/simulavr`` in
  gdb-server mode and drives it over a localhost socket.  Upstream's suite is
  Python 2; patch ``0004`` ports the ``regress/`` harness to Python 3 (required
  for the suite to even parse: original 85/120 files fail to byte-compile under
  Python 3; ported 119/120, the remainder an unused ``modtest`` helper).
- Docs: ``configure.ac`` hard-errors when ``makeinfo`` is absent and ``doc/``
  builds ``simulavr.info`` via ``$(MAKEINFO)``; CI has no texinfo, so
  ``MAKEINFO=true`` is injected (knowledge DRAFT-libgtop-makeinfo-missing —
  same effect as the upstream ``--disable-makeinfo`` fallback).

Compiler-header fixes carried in ``patches/`` (all three found by cross
compiling every ``pkginclude_HEADERS`` translation unit with the OHOS clang 15
+ libc++ toolchain; see notes.md for the sweep evidence):
- avrfactory.h needs ``<map>`` (declares a ``std::map`` member; libc++ does
  not include <map> transitively the way libstdc++ does);
- avrmalloc.h needs ``<stddef.h>`` (uses ``size_t`` in prototypes);
- cmd/gdbserver.cpp calls POSIX ``bind()`` under ``using namespace std``,
  where the C++ ``std::bind`` overload wins name lookup -> qualify ``::bind``.
"""

import os
import shlex
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    copy, get, apply_conandata_patches, export_conandata_patches,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SimulavrConan(ConanFile):
    name = "simulavr"
    version = "1.0.0-git20160221.e53413b"
    description = ("AVR microcontroller simulator (libsim simulation library "
                   "+ simulavr gdb-server CLI)")
    license = "GPL-2.0-or-later"
    homepage = "https://www.nongnu.org/simulavr/"
    url = "https://savannah.nongnu.org/projects/simulavr"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # Ship the pre-generated autotools files (configure, Makefile.in, ...)
        # as plain text under preconf/ (recipe cache via exports_sources ->
        # self.export_sources_folder/preconf).  See preconf/README.md.
        copy(self, "preconf/*", self.recipe_folder, self.export_sources_folder)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "simulavr is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        # The Debian pristine orig tarball has no single root directory
        # (top level is configure.ac + src/ + regress/ + ...), so strip_root
        # must stay disabled: enabling it would scramble the tree.
        get(self, **self.conan_data["sources"], strip_root=False)
        apply_conandata_patches(self)
        # Overlay the pre-generated autotools build system (no autoreconf on
        # the build host — see module docstring).
        preconf = os.path.join(self.export_sources_folder, "preconf")
        if os.path.isdir(preconf):
            copy(self, "*", preconf, self.source_folder)
        else:
            raise ConanInvalidConfiguration(
                "preconf/ missing from exported sources — cannot bootstrap "
                "the autotools build system on OHOS")
        # The bundled ElfIO keeps a 62-byte marker file named VERSION in
        # src/elfio/.  src/elfio is on the include path (-I<srcdir>/elfio), so
        # any `#include <version>` inside the C++ standard library resolves to
        # that plain-text marker instead of libc++'s <version> header, and the
        # compiler chokes on its content ("unknown type name 'This'") deep
        # inside <iostream>/<memory>.  <version> is included transitively by
        # many libc++ headers, so this breaks ordinary translation units.  The
        # file is only a human-readable version note and is not used by the
        # build, so drop it (same class as the gettext "intl/version" shadow).
        for name in ("VERSION", "version"):
            marker = os.path.join(self.source_folder, "src", "elfio", name)
            if os.path.isfile(marker):
                os.remove(marker)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        # Upstream auto-detects optional integrations that are not part of
        # this deliverable and are absent on OHOS (Tcl/Tk interface, SWIG
        # python module, Icarus Verilog VPI module).
        tc.configure_args.append("--disable-tcl")
        tc.configure_args.append("--disable-python")
        tc.configure_args.append("--disable-verilog")
        # configure.ac hard-errors when makeinfo is missing, and doc/ builds
        # simulavr.info through $(MAKEINFO); CI has no texinfo.  Injecting
        # MAKEINFO=true makes configure skip the error and turn the .info
        # recipe into a no-op (docs are not a deliverable).
        tc.configure_args.append("MAKEINFO=true")
        # Upstream configure.ac does `AC_CHECK_PROG(CXX_PROG, ${CXX}, yes, no)`
        # and `AC_CHECK_PROG(MAKEINFO_PROG, makeinfo, yes, no)` and turns a
        # "no" into AC_MSG_ERROR.  AC_CHECK_PROG searches PATH by concatenating
        # each PATH entry with the program name, so it only works for a *bare*
        # name; Conan exports CXX as an absolute path
        # (/data/service/hnp/bin/clang++), which the PATH-join can never match
        # ("checking for /data/service/hnp/bin/clang++... no").  The compiler is
        # demonstrably usable (the C++11/ld/PIC probes just before it succeed),
        # and makeinfo is intentionally absent, so satisfy both existence checks
        # via their autoconf cache variables instead of weakening the build.
        tc.configure_args.append("ac_cv_prog_CXX_PROG=yes")
        tc.configure_args.append("ac_cv_prog_MAKEINFO_PROG=yes")
        # simulavr predates C++17 and its own ``typedef unsigned char byte`` in
        # types.h collides with libc++'s C++17 ``std::byte``: any translation
        # unit that has ``using namespace std;`` plus a standard header (which
        # pulls <cstddef>) then sees ``byte`` as ambiguous
        # (e.g. cmd/gdb.h: `void avr_core_flash_write_lo8(int, byte)`).  Build
        # as C++14 — exactly what Debian's own packaging does for this source
        # (debian/rules: DEB_CXXFLAGS_MAINT_APPEND = -std=c++14), and enough for
        # this 2016 C++ code.  Appended after the toolchain's -std=gnu++17 so it
        # takes effect.
        tc.extra_cxxflags.append("-std=gnu++14")
        tc.generate()

    def _ensure_toolchain_on_path(self):
        # The runner's base PATH does not include the toolchain bin directory
        # (/data/service/hnp/bin holds make/clang/m4/perl/autoreconf).  self.run
        # (env="conanbuild") inherits the process environment for variables the
        # env file does not define, so prepend the compiler directory (taken
        # from the profile conf, R33 — no hardcoded absolute path) to PATH.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c")
        if not cc or not os.path.isfile(cc):
            return
        cc_dir = os.path.dirname(cc)
        path = os.environ.get("PATH", "")
        if cc_dir and cc_dir not in path.split(os.pathsep):
            os.environ["PATH"] = cc_dir + os.pathsep + path

    def _make_build_helpers_executable(self):
        for relative in ("configure", "config.guess", "config.sub",
                         "install-sh", "missing", "depcomp", "ar-lib",
                         "compile", "doc/mdate-sh"):
            path = os.path.join(self.source_folder, relative)
            if os.path.isfile(path):
                mode = os.stat(path).st_mode
                os.chmod(path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def build(self):
        self._make_build_helpers_executable()
        self._ensure_toolchain_on_path()

        # Autoconf-era scripts create temporary dirs with umask 077, which can
        # leave generated files inaccessible on HMDFS; redirect TMPDIR into the
        # build folder.  Pin a plain shell (the hnp /data/service/hnp/bin/bash
        # has getcwd issues on HMDFS, E386).
        if str(self.settings.os) == "OHOS":
            tmp_dir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmp_dir, exist_ok=True)
            os.environ["TMPDIR"] = tmp_dir
            os.environ.setdefault("CONFIG_SHELL", "/system/bin/sh")

        autotools = Autotools(self)
        # HMDFS preserves job-user files as non-executable (mode bits are
        # clamped and the MAC policy denies execve of anything outside the
        # signed tool areas), so run configure through the shell that VFS
        # allows reading: `<shell> <configure> <args>`.  Same idiom as
        # duff/0.5.2 (the only known autotools package that builds on this
        # device); plain `autotools.configure()` exec's ./configure directly
        # and would fail with EACCES (126).
        configure_script = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_script):
            configure_script = os.path.join(self.build_folder, "configure")
        configure_shell = ("/system/bin/sh" if str(self.settings.os) == "OHOS"
                           else (os.environ.get("CONFIG_SHELL") or "/bin/sh"))
        configure_tmp = os.environ.get("TMPDIR",
                                       os.path.join(self.build_folder, "tmp"))
        self.run(
            "cd {b} && TMPDIR={t} CONFIG_SHELL={s} SHELL={s} {s} {c} {args}".format(
                b=shlex.quote(self.build_folder.replace("\\", "/")),
                t=shlex.quote(configure_tmp.replace("\\", "/")),
                s=shlex.quote(configure_shell),
                c=shlex.quote(configure_script.replace("\\", "/")),
                args=autotools._configure_args),
            env="conanbuild")

        # Keep automake regeneration rules from firing (no automake on the
        # host; generated files are the source of truth — E248), and silence
        # the ACLOCAL/AUTOMAKE/AUTOCONF/AUTOHEADER probes that would run them.
        make_args = [
            "-j1",                      # E074: HMDFS jobserver fifo EPERM
            "-o", "Makefile",
            "-o", "config.status",
            "ACLOCAL=/bin/true", "AUTOMAKE=/bin/true",
            "AUTOCONF=/bin/true", "AUTOHEADER=/bin/true",
        ]
        autotools.make(args=make_args)
        # R51: attempt to run the upstream suite (make check -> regress.py ->
        # the freshly built src/simulavr driven over a localhost gdb socket).
        # regress.py spawns src/simulavr, and this device's HMDFS denies execve
        # of the job user's own build artifacts (nosuid + MAC), so the suite may
        # not be able to launch the simulator.  Record the real outcome instead
        # of masking it: the exit code is surfaced in the log and reported in
        # notes.md / the PR (never silently claimed as "passed").
        rc = self.run(
            "make {} {}".format(" ".join(make_args), "check"),
            cwd=self.build_folder, env="conanbuild", ignore_errors=True)
        self.output.info("UPSTREAM make check exit code = {}".format(rc))

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Drop libtool *.la wrappers (they embed build-machine paths).
        for root, _dirs, files in os.walk(self.package_folder):
            for name in files:
                if name.endswith(".la"):
                    os.remove(os.path.join(root, name))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING", src=os.path.join(self.source_folder, "src",
                                               "elfio"),
             dst=os.path.join(self.package_folder, "licenses", "elfio"))

    def package_info(self):
        # simulavr is delivered as the upstream CLI (bin/simulavr).  libsim is
        # linked into it as a convenience library (see preconf/README.md), so
        # there is no standalone library to expose.  R38/CI L0k require the
        # bindirs declaration for CLI packages, and preflight PF8 then requires
        # archives/s/simulavr/commands.json (which is present).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
