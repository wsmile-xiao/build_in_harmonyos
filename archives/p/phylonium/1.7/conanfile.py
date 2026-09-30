"""Conan recipe for phylonium 1.7 - estimation of evolutionary distances.

phylonium reads FASTA files (one file per genome) and prints a symmetric
distance matrix in PHYLIP format (see Readme.md / man/phylonium.1.in). It is a
C++ command line tool: `bin_PROGRAMS = phylonium` in src/Makefile.am, so the
package_type is "application" and the software-level commands.json declares it.

Adaptation decisions (all traceable to upstream files or this repo's E-entries):

- Source is the official GitHub tag archive v1.7. The Ubuntu pool
  phylonium_1.7.orig.tar.gz is a Debian re-compression that drops .travis.yml
  and must not be used (R39).
- The tag archive ships only configure.ac/Makefile.am - no generated configure,
  no config.hin (configure.ac:85 names `config.h:config.hin` and 7 files
  #include "config.h"), so build() must bootstrap with `autoreconf` exactly as
  the upstream Readme prescribes (`autoreconf -fi -Im4`); autoheader then
  creates the config.hin template. automake also installs its test-driver,
  which the top-level TESTS harness needs.
- libdivsufsort64 is an unconditional hard dependency: configure.ac:43-48 calls
  AC_MSG_ERROR([Missing libdivsufsort64.]) with no --disable switch, probing
  divsufsort64.h + the divsufsort64 symbol. libdivsufsort/2.0.1 is required as
  a host dependency (its published static package has divsufsort64=True, so the
  component name matches the probe); AutotoolsDeps supplies -ldivsufsort64 and
  the include dir through the conanbuild environment that self.run() applies.
- --disable-x86simd --disable-avx512: configure.ac:50-67 defaults BOTH to
  enabled with no CPU autodetection, and libs/Makefile.am would then compile
  -msse2/-mavx2/-mavx512bw sources on aarch64.
- AC_PROG_RANLIB + noinst_LIBRARIES in libs/Makefile.am: archives only, nothing
  to install from libs/, so no shared/fPIC options are declared (a program has
  no shared flavor).
- AX_CXX_COMPILE_STDCXX(17) plus the hard-coded -std=c++17 in
  test/Makefile.am pin C++17; the tree has no dynamic exception specifications
  and no `register`, so compiler.cppstd is deliberately NOT dropped here.
- configure is launched with CONFIG_SHELL/SHELL routed back to /bin/sh
  (_configure_with_binsh): the shared ci/conan/profiles/ohos-aarch64 exports
  hnp bash as the shell, and that shell cannot getcwd() inside the conan cache
  dirs on HMDFS, which makes autoconf's re-exec prologue die with "working
  directory cannot be determined" (E386). The generated configure is also
  relaxed for HMDFS the same way (_patch_generated_configure, E011/E114).
- make runs with -j1: HMDFS has no mkfifo, so the make jobserver is
  unavailable at -j>1, and -j1 additionally honours the device concurrency
  discipline.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import load_toolchain_args
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PhyloniumConan(ConanFile):
    name = "phylonium"
    version = "1.7"
    description = ("phylonium - fast and accurate estimation of evolutionary "
                   "distances between closely related genomes from FASTA files")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/EvolBioInf/phylonium"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # Upstream ships no license file at all, so the canonical GPLv3+ text lives
    # next to the recipe and must travel with it (R39/CI junk rules).
    exports_sources = "licenses/*.txt"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("libdivsufsort/2.0.1")

    def build_requirements(self):
        # No pre-generated configure in the official tag archive, so the
        # autotools must come from the registry rather than the build host
        # (checklist #3). Versions pinned to what is both archived and
        # published as an OHOS binary: note that libtool/2.5.4 lists a remote
        # package but has no archive directory, and automake/1.17 has a
        # directory but no conanfile.py - both would fail graph resolution.
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4.1")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Both default to enabled upstream with no CPU probe; aarch64 must turn
        # them off or libs/, src/ and test/ compile x86 SIMD intrinsics.
        tc.configure_args.append("--disable-x86simd")
        tc.configure_args.append("--disable-avx512")
        tc.generate()
        # AutotoolsDeps, not hand-written flags: configure probes
        # AC_CHECK_HEADERS(divsufsort64.h) + AC_CHECK_LIB(divsufsort64,...), so
        # CPPFLAGS and LIBS must carry the dependency (R33 forbids raw shell
        # variables).
        deps = AutotoolsDeps(self)
        deps.generate()

    def _autoreconf_command(self):
        """Bootstrap with a single, consistent perl (knowledge DRAFT-6049).

        The plain `autoreconf -fi` failed on device with

            Can't load '.../perl/5.42.2/aarch64-linux-thread-multi/.../Cwd.so'
            for module Cwd: Error relocating ...: Perl_my_cxt_init: symbol not found
            Compilation failed in require at /data/service/hnp/bin/autoreconf line 48

        because conanbuild's PERL5LIB points at the conan perl/5.42.2
        (aarch64-linux-thread-multi) library dirs while the autoreconf that PATH
        resolves first is the hnp one running the *system* perl; the two 5.42.2
        flavours have incompatible arch dirs, so the XS module cannot be
        relocated. Same family as the "handshake mismatch" recorded for
        libnxml 0.18.5.

        Fix (device-verified there): unify the interpreter on the system perl and
        narrow PERL5LIB to the two pure-Perl module dirs, so every XS module
        falls back to the system perl's own @INC and stays same-origin with the
        binary. The conan autoconf/m4 bin dirs are prepended so the packaged
        autoconf is the one that runs, and `-Im4` matches the upstream Readme
        (`autoreconf -fi -Im4`), which the AC_CONFIG_MACRO_DIR([m4]) probe of
        ax_*.m4 needs.
        """
        prefix = []
        for ref in ("autoconf/2.72", "m4/1.4.19"):
            try:
                bindir = self.dependencies.build[ref].cpp_info.bindirs[0]
            except KeyError:
                continue
            if os.path.isdir(bindir):
                prefix.append(bindir)
        am = self.dependencies.build["automake/1.18"]
        ac = self.dependencies.build["autoconf/2.72"]
        am_share = os.path.join(am.package_folder, "share", "automake-1.18")
        ac_share = os.path.join(ac.package_folder, "share", "autoconf")
        for d in (am_share, ac_share):
            if not os.path.isdir(d):
                raise ConanException("autotools share dir not found: %s" % d)
        return ('PATH="%s:$PATH" PERL=perl PERL5LIB="%s:%s" autoreconf -fi -Im4'
                % (":".join(prefix), am_share, ac_share))

    def _patch_generated_configure(self):
        """Relax the two HMDFS-hostile spots in the autoreconf output.

        E011/E114: config.status creates its temp dir under `umask 077`; HMDFS
        maps the resulting 0700+setgid dir to file_manager so the building
        process cannot write into it and config.status silently produces no
        Makefile/config.h.
        E386: the autoconf >= 2.70 re-exec check uses `pwd`, which fails in
        some HMDFS cwd states even though $PWD is valid -> fall back to $PWD.
        Applied after autoreconf because bootstrapping regenerates configure
        from scratch; both replacements are no-ops when the needle is absent.
        """
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            return
        with open(configure, "r", encoding="utf-8", errors="ignore") as handle:
            text = handle.read()
        original = text
        text = text.replace("umask 077", "umask 022")
        needle = 'ac_pwd=`pwd` && test -n "$ac_pwd" &&'
        if needle in text:
            text = text.replace(
                needle,
                'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"\ntest -n "$ac_pwd" &&',
                1,
            )
        if text != original:
            with open(configure, "w", encoding="utf-8") as handle:
                handle.write(text)
            self.output.info("patched generated configure for HMDFS "
                             "(E011/E114 umask, E386 ac_pwd fallback)")

    def _configure_with_binsh(self):
        """Run configure with the shell routed back to /bin/sh (E386).

        The framework profile ci/conan/profiles/ohos-aarch64 pins
        [buildenv] CONFIG_SHELL=SHELL=/data/service/hnp/bin/bash, and autoconf's
        prologue re-execs configure through $CONFIG_SHELL; hnp bash cannot
        getcwd() in the conan cache dirs on HMDFS, so configure aborts with
        "working directory cannot be determined". self.run() still applies the
        conanbuild environment (ConanFile.run defaults env to "conanbuild" for
        scope="build"), so AutotoolsDeps' CPPFLAGS/LIBS and the toolchain's
        CC/CXX keep flowing - only the two shell variables change.
        The argument list is read back from the generated toolchain file, so
        --prefix and the dependency flags are not hand-copied.
        """
        configure = os.path.join(self.source_folder, "configure")
        args = load_toolchain_args(self.generators_folder).get("configure_args", "") or ""
        self.run('env CONFIG_SHELL=/bin/sh SHELL=/bin/sh /bin/sh "{}" {}'.format(
            configure, args))

    def _report_upstream_tests(self):
        """Print automake's own summary so the test numbers are traceable.

        automake writes test-suite.log (aggregate) plus one .log/.trs per TEST
        into the top build directory. This is reporting only: `make check`
        already failed the build if any registered test failed.
        """
        for name in ("test-suite.log",):
            path = os.path.join(self.build_folder, name)
            if not os.path.isfile(path):
                self.output.warning("upstream test summary %s not found in %s"
                                    % (name, self.build_folder))
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                body = handle.read()
            for line in body.splitlines():
                if line.startswith("# ") or line.startswith("#:"):
                    self.output.info("[upstream make check] %s" % line)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # Upstream's own instruction is `autoreconf -fi -Im4`: the tag archive
        # commits no configure/aclocal.m4/Makefile.in, and autoheader is what
        # creates the config.hin template that configure.ac:85 requires. Run it
        # in the source folder with the interpreter unified per
        # _autoreconf_command (plain autotools.autoreconf() fails on device).
        self.run(self._autoreconf_command(), cwd=self.source_folder,
                 env="conanbuild")
        self._patch_generated_configure()
        self._configure_with_binsh()
        autotools.make(args=["-j1"])
        # Upstream tests must really execute (§10 / R51). automake registers
        # exactly 2 TESTS at the top level (Makefile.am:10
        # TESTS=test/simple.sh test/unittests); test/unittests is a Catch
        # runner holding the 6 TEST_CASEs, and simf is only built as a
        # check_PROGRAM and consumed *by* simple.sh, so it is not a third test.
        # SUBDIRS = libs src test . makes this recursive, and the trailing "."
        # is what runs the top-level TESTS.
        autotools.make(target="check", args=["-j1"])
        self._report_upstream_tests()

    def package(self):
        autotools = Autotools(self)
        # -j1 explicitly: without it conan appends -j<build_jobs>, and HMDFS has
        # no mkfifo so the make jobserver is unavailable (see build()).
        autotools.install(args=["-j1"])
        # Upstream ships no license text at all (probed 9 candidate filenames on
        # both tag v1.7 and master - all 404), while every source file carries
        # "SPDX-License-Identifier: GPL-3.0-or-later" and the Readme points at
        # gnu.org. So the canonical text is shipped from the recipe folder, not
        # fabricated here.
        # Note the folder: exports_sources land in export_sources_folder (the
        # cache "es" dir); self.recipe_folder is the "e" dir and holds only the
        # recipe, which is why pointing at recipe_folder silently packaged 0
        # licenses on the first device run.
        copy(self, "*.txt",
             src=os.path.join(self.export_sources_folder, "licenses"),
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        for required in ("licenses/GPL-3.0-or-later.txt",):
            if not os.path.isfile(os.path.join(self.package_folder, *required.split("/"))):
                raise ConanException("missing packaged file: %s" % required)
        program = os.path.join(self.package_folder, "bin", "phylonium")
        if not os.path.isfile(program):
            raise ConanException(
                "package() found no bin/phylonium under %s; make install did "
                "not deliver the program" % self.package_folder)
        # E543: HMDFS hands newly created files mode 660, which leaves the
        # delivered binary non-executable. chmod is best-effort (E046: HMDFS can
        # ignore chmod) - the hard contract is asserted by test_package.
        try:
            os.chmod(program, 0o755)
        except OSError as error:  # pragma: no cover - platform dependent
            self.output.warning("chmod +x on %s failed: %s" % (program, error))

    def package_info(self):
        # R38: application package; the software-level commands.json declares
        # the single `phylonium` tool. Nothing is exported as a C++ target.
        self.cpp_info.bindirs = ["bin"]
