#!/usr/bin/env python3
"""Conan recipe for ifile 1.3.9 - a naive-Bayes mail filter for MH/exmh.

ifile is a command-line tool (C, autoconf 2.59 era) that trains on mail messages
read from standard input and then classifies further messages.  It bundles its
own copy of GNU argp (argp/) as a second autoconf project.

Adaptation points, each one verified on HarmonyOS PC (evidence in notes.md):

* E011 - the generated ``configure`` builds config.status' scratch directory
  with ``(umask 077 && mktemp -d)``, which on HMDFS comes out unwritable, so
  ``./config.status`` cannot write ``subs.sed``.  ``patches/0001`` and
  ``patches/0002`` relax it to ``umask 022`` for the top-level and the bundled
  argp project respectively; the temp-directory logic itself is kept.
* DRAFT-ifile-1.3.9-extern-inline - ``argp/argp.h`` sets ``ARGP_EI=extern
  inline`` and puts the *definitions* of argp_usage/_option_is_short/
  _option_is_end (plus the eight ``argp_fmtstream_*`` in argp-fmtstream.h) in
  the header.  Under clang 15's default C17 inline semantics every translation
  unit including argp.h emits a strong out-of-line copy, so the final link dies
  with 20 ``ld.lld: error: duplicate symbol``.  Upstream itself assumes GNU89
  semantics - argp-fs-xinl.c blanks ARGP_FS_EI so exactly one TU provides the
  definitions - hence ``-fgnu89-inline``.  ``-fcommon``, the documented fix for
  header-defined *variables*, does nothing for this.
* patches/0003 - ``ifile.c`` took its inter-job lock with System V semaphores
  (``semget``/``semop``) as the first thing ``main()`` does.  This platform's
  seccomp policy kills the process with SIGSYS for any SysV IPC syscall, so even
  ``ifile --version`` could not run and no errno branch is ever reached.  The
  lock becomes ``flock(LOCK_EX)`` on a per-user lock file, which keeps the
  original SEM_UNDO release-on-exit property.
* patches/0004 - two shell statements were left in ``Makefile.in``; GNU make
  rejects them with "Makefile:57: *** missing separator".
* ar/ranlib - autoconf 2.59 predates ``AC_PROG_AR``, so ``$(AR)`` stays make's
  bare default ``ar`` (and argp's Makefile hardcodes it), which is not on the
  OHOS toolchain PATH.  A private shim directory maps the bare names onto
  ``llvm-ar``/``llvm-ranlib``.
* install - the upstream rule is ``cd $(mandir)/man1 ; rm -f $(MAN_1_PAGES)``
  with no ``$(DESTDIR)`` on the cd, so the conventional
  ``make install DESTDIR=<pkg>`` lets the cd fail and then deletes the *source*
  man page before installing it.  Install is therefore driven with absolute
  ``prefix``/``bindir``/``mandir`` and no DESTDIR, and ``INSTALL`` is pinned to
  the portable ``install-sh`` shipped in the tarball, because ``AC_PROG_INSTALL``
  otherwise bakes an absolute host path the CI worker PATH will not have.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class IfileConan(ConanFile):
    name = "ifile"
    version = "1.3.9"
    description = (
        "ifile - intelligent mail filter for EXMH/MH: a naive-Bayes message "
        "classifier that learns from mail folders and sorts further messages"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://people.csail.mit.edu/jrennie/ifile/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # ifile builds in-tree: its Makefile rewrites $(srcdir)/include/ifile.h
        # from $(srcdir)/Version, and its own test.sh runs
        # ./configure && make && make install assuming srcdir == builddir.
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ tools --

    def _cc(self, compilers=None):
        if compilers is None:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
        cc = compilers.get("c")
        if cc and os.path.exists(cc):
            return cc
        return shutil.which("clang") or "clang"

    def _llvm_tool(self, logical):
        """Absolute path of an llvm binutils tool for the active toolchain.

        The shared OHOS profile puts only c/cpp into
        tools.build:compiler_executables, so derive the rest from the compiler
        directory and only then fall back to PATH.  Never hand back a bare name:
        the CI worker PATH has neither the toolchain dir nor `ar`.
        """
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cand = compilers.get(logical)
        if cand and os.path.exists(cand):
            return cand
        cc = self._cc(compilers)
        cand = os.path.join(
            os.path.dirname(os.path.realpath(cc)), "llvm-" + logical
        )
        if os.path.exists(cand):
            return cand
        cand = shutil.which("llvm-" + logical) or shutil.which(logical)
        if not cand or not os.path.exists(cand):
            raise RuntimeError(
                f"no usable '{logical}' found (compiler_executables={compilers})"
            )
        return cand

    def _tool_shims(self):
        """Expose bare `ar`/`ranlib` for autoconf-2.59-era makefiles."""
        bindir = os.path.join(self.build_folder, "_toolbin")
        os.makedirs(bindir, exist_ok=True)
        for logical in ("ar", "ranlib"):
            target = self._llvm_tool(logical)
            link = os.path.join(bindir, logical)
            if os.path.lexists(link):
                os.remove(link)
            os.symlink(target, link)
            self.output.info(f"tool shim: {logical} -> {target}")
        env = Environment()
        env.prepend_path("PATH", bindir)
        env.vars(self, scope="build").save_script("conanbuild_ifile_toolbin")

    # -------------------------------------------------------------- generate --

    def generate(self):
        tc = AutotoolsToolchain(self)
        # argp's headers are written for GNU89 `extern inline`; under clang 15's
        # default C17 inline semantics each includer emits a strong copy.
        tc.extra_cflags.append("-fgnu89-inline")
        # util.c:49 ifile_sprintf() puts its own vsprintf() *inside* assert(), so
        # the Release-mode -DNDEBUG that conan injects through CPPFLAGS does not
        # merely skip a check - it deletes the formatting call, and every path the
        # program then builds is the empty string.  -UNDEBUG restores upstream
        # semantics (its own CFLAGS carry no NDEBUG).  Clearing CPPFLAGS on the make
        # command line, the trick used for braa, is not available here because
        # CPPFLAGS also carries the -I flags conan generated.  (Same mechanism as
        # 适配经验汇总 12.11a; that entry's fix is the -UNDEBUG variant now.)
        tc.extra_cflags.append("-UNDEBUG")
        # Pass both triplets: telling autoconf 2.59 OHOS for build *and* host
        # makes it mis-guess the build type.
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # autoconf 2.59 predates --datarootdir/--localedir (added in 2.60/2.63)
        # and aborts on "unrecognized option" for them.
        tc.update_configure_args({"--datarootdir": None, "--localedir": None})
        tc.generate()
        self._tool_shims()

    # ------------------------------------------------------------------ build --

    def build(self):
        apply_conandata_patches(self)

        autotools = Autotools(self)
        autotools.configure()
        # argp/ is a separate autoconf project the top-level Makefile only
        # reaches through `cd argp ; $(MAKE) libargp.a`, so it needs its own
        # config.status.  Run it inside argp/: invoked from the project root its
        # generated Makefile would land in the wrong directory.
        self.run(
            "./configure --prefix=/usr"
            " --build=aarch64-unknown-linux-gnu"
            " --host=aarch64-unknown-linux-ohos",
            cwd=os.path.join(self.build_folder, "argp"),
        )
        autotools.make(args=["-j1"])
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Execute upstream's own test.sh (R51) and report it honestly.

        test.sh holds 8 assertions over the `make install` layout.  Two
        mechanical rewrites are applied and nothing else: its /tmp install
        targets move inside the build folder (/tmp is read-only on this device),
        and the bash-only `&>` redirection becomes POSIX `> /dev/null 2>&1`.
        Assertions 4-7 can never pass on any release: they look for ifilter.mh,
        irefile.mh, knowledge_base.mh and news2mail, which upstream deleted while
        leaving the suite untouched (ChangeLog: "ifilter.mh.pl, irefile.mh.pl,
        knowledge_base.mh.pl, news2mail.pl: removed (added to new mh-ifile)").
        The four live assertions gate the build; the four stale ones are
        reported, not hidden.
        """
        src = os.path.join(self.source_folder, "test.sh")
        if not os.path.isfile(src):
            raise RuntimeError("upstream test.sh disappeared from the source tree")
        with open(src, encoding="utf-8", errors="replace") as handle:
            body = handle.read()
        root = os.path.join(self.build_folder, "_testroot")
        install_sh = os.path.join(self.source_folder, "install-sh")
        for old, new in (
            ("/tmp/linux", os.path.join(root, "linux")),
            ("/tmp/foobin", os.path.join(root, "foobin")),
            ("/tmp/fooman", os.path.join(root, "fooman")),
            ("/tmp/man", os.path.join(root, "man")),
            ("--exec-prefix=/tmp", f"--exec-prefix={root}"),
            ("--prefix=/tmp", f"--prefix={root}"),
            ("&> /dev/null", "> /dev/null 2>&1"),
            # The suite's own `make install` would otherwise use whatever
            # AC_PROG_INSTALL baked on that machine (the CI worker and this
            # device resolve different programs, and a host `install` that
            # rejects `-c` silently drops the man page).  Pin it to the portable
            # install-sh that ships with the tarball; command-line variables
            # override the Makefile, so the assertions themselves are untouched.
            ("make install",
             f"make install INSTALL='{install_sh} -c' STRIP="),
        ):
            body = body.replace(old, new)
        script = os.path.join(self.build_folder, "test-upstream.sh")
        with open(script, "w", encoding="utf-8") as handle:
            handle.write(body)

        self.run("sh test-upstream.sh > test-upstream.log 2>&1 || true")
        with open(os.path.join(self.build_folder, "test-upstream.log"),
                  encoding="utf-8", errors="replace") as handle:
            log = handle.read()
        passed = [ln for ln in log.splitlines() if ln.startswith("ok ")]
        failed = [ln.split()[2] for ln in log.splitlines()
                  if ln.startswith("not ok ")]
        self.output.info(
            f"upstream test.sh: {len(passed)} ok / {len(failed)} not ok of 8; "
            f"not-ok ids = {failed}"
        )
        stale = {"4", "5", "6", "7"}
        gating = sorted(set(failed) - stale)
        if len(passed) != 4 or gating:
            # Dump the evidence rather than just the counts: the CI worker runs in
            # a different environment from any dev shell, and without the install
            # transcript a failed assertion is undiagnosable from the log alone.
            listing = os.path.join(self.build_folder, "_testroot_listing.txt")
            self.run(f'find "{root}" -type f > "{listing}" 2>&1 || true',
                     ignore_errors=True)
            try:
                with open(listing, encoding="utf-8", errors="replace") as handle:
                    found = handle.read()
            except OSError:
                found = "(no files under _testroot)"
            self.output.warning("=== test-upstream.sh transcript ===\n" + log)
            self.output.warning("=== installed files under _testroot ===\n" + found)
            raise RuntimeError(
                "upstream test.sh did not produce the expected four passing "
                f"install-layout assertions (ok={len(passed)}, unexpected "
                f"failures={gating}); the transcript and file listing are above"
            )

    # ---------------------------------------------------------------- package --

    def package(self):
        pkg = self.package_folder
        install_sh = os.path.join(self.source_folder, "install-sh")
        autotools = Autotools(self)
        # Absolute prefix/bindir/mandir and no DESTDIR - see the module
        # docstring.  STRIP is emptied because the rule splices $(STRIP) into the
        # install options, and a stripped binary is rejected by the OHOS MAC.
        autotools.make(
            target="install",
            args=[
                f"prefix={pkg}",
                f"bindir={os.path.join(pkg, 'bin')}",
                f"mandir={os.path.join(pkg, 'share', 'man')}",
                f'INSTALL="{install_sh} -c"',
                "STRIP=",
            ],
        )
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(pkg, "licenses"))
        binary = os.path.join(pkg, "bin", "ifile")
        if not os.path.isfile(binary):
            raise RuntimeError("package step produced no bin/ifile")
        os.chmod(binary, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
