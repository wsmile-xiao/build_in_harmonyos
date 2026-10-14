#!/usr/bin/env python3
"""Conan recipe for spigot 0.2017-01-15.gdad1bbc6 — Simon Tatham's exact real calculator.

spigot evaluates a mathematical expression to any requested precision by
computing digits one at a time (spigot algorithm), optionally accelerating
the big-integer layer with GMP and the terminal line editor with ncurses.
Build system is autotools; the product is a single command-line executable.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                               get, replace_in_file)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SpigotConan(ConanFile):
    name = "spigot"
    version = "0.2017-01-15.gdad1bbc6"
    description = "Exact real calculator: evaluates a mathematical expression to any desired precision"
    license = "MIT"
    homepage = "http://www.chiark.greenend.org.uk/~sgtatham/spigot/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Single command-line executable, no library to link against (R38: the
    # software-level commands.json is what declares the binary).
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    generators = "AutotoolsDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Big-integer arithmetic provider (configure.ac: --with-gmp).
        self.requires("gmp/6.3.0")
        # Terminal handling for the interactive line editor
        # (configure.ac: AC_SEARCH_LIBS(tigetstr, tinfo ncurses)).
        self.requires("ncurses/6.6")

    def build_requirements(self):
        # The tarball ships configure.ac + Makefile.am + autogen.sh but NOT a
        # generated `configure`, so autotools have to be bootstrapped. halibut is
        # required for the same reason Debian lists it in Build-Depends: the
        # tarball carries the .but documentation sources but not the generated
        # spigot.1 / spigot.html that Makefile.am installs, and configure only
        # defines the rules to build them when `halibut` is on PATH
        # (AC_CHECK_PROG([HALIBUT]) -> AM_CONDITIONAL(HAVE_HALIBUT)). Without
        # halibut, `make install` dies on man1_MANS = spigot.1.
        # autoconf/automake/m4/perl are taken from the build machine, the same
        # way the other recipes in this repo that shell out to `autoreconf` do.
        # CI worker PATH has autoreconf (autoconf 2.72) but NO aclocal (automake
        # is absent: `autoreconf: error: aclocal failed`), so automake must be
        # pulled in as a tool_requires like the abiword-* recipes (artifact repo
        # publishes automake/1.18).
        self.tool_requires("automake/1.18")
        self.tool_requires("halibut/1.3")

    def layout(self):
        # autoreconf, configure and make all run in the unpacked source tree:
        # spigot has no libtool, no subprojects and no out-of-tree build
        # support, and Makefile.am's `test` target invokes $(srcdir)/test.sh.
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R15/E007: never pass --build/--host/--target. spigot's configure.ac has
        # no AC_CANONICAL_HOST and `autoreconf -i` does not install
        # config.guess/config.sub for such a package, so this is a plain native
        # build that configure resolves on its own -- which also means no
        # config.guess/config.sub OHOS patch is required (verified: the build
        # tree after `autoreconf -v -i -f` contains neither file).
        tc.configure_args = [a for a in tc.configure_args
                             if not str(a).startswith(("--build=", "--host=", "--target="))]
        # Upstream default is `--with-gmp=check`; be explicit so the GMP bigint
        # provider is a hard requirement of this build rather than a lucky probe.
        tc.configure_args.append("--with-gmp")
        # version.h ships `#define VER "unidentified build"` guarded by #ifndef,
        # and upstream commit dad1bbc6 ("Permit overriding VER on the make
        # command line") added the hook, so stamp the real version into
        # `spigot --version`.
        tc.extra_cxxflags.append("-DVER='\"{}\"'".format(self.version))
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # 1) Bootstrap: the tarball has no `configure`.
        self.run("autoreconf -v -i -f")

        # 2) E114/E011: on HMDFS the `(umask 077 && mktemp ...)` temp dir that
        #    the generated configure/config.status create is not writable by the
        #    building process. 077 -> 022 (htop / bwm-ng / cproto precedent).
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            replace_in_file(self, configure, "umask 077", "umask 022", strict=False)

        autotools = Autotools(self)
        # 3) ncurses/6.6 only ships libncursesw.a (no libtinfo.a / libncurses.a),
        #    so upstream's `AC_SEARCH_LIBS(tigetstr, tinfo ncurses)` matches
        #    neither candidate and appends nothing to LIBS -- that macro only
        #    searches while the symbol is still undeclared, and at that point
        #    ncurses.h has not been included yet. main.cpp nevertheless calls
        #    tigetstr()/tparm()/setupterm() (AC_CHECK_HEADERS([ncurses.h]) does
        #    succeed off the -I path), so the link dies with
        #      undefined symbol: tigetstr / tparm / setupterm
        #    nm on libncursesw.a shows tigetstr/tparm/setupterm/tiparm are all
        #    defined there. Passing LIBS as a configure precious-variable
        #    assignment makes the search report "none required" and links the
        #    wide-character ncurses that actually exists.
        autotools.configure(args=["LIBS=-lncursesw"])
        # R9: single job -- parallel make trips the HMDFS jobserver fifo EPERM (E074).
        # `make` also generates spigot.1 + spigot.html through the halibut rules,
        # which is what makes the later `make install` able to install them.
        autotools.make(args=["-j1"])

        # 3) Upstream test suite, run for real in the build phase.
        #    test.sh is bash and drives ./spigot through 1133 testcases
        #    (exact-digit comparisons across trig / bigint / zeta / continued
        #    fractions / bases / formatting), printing "pass N / fail N /
        #    total N" and exiting nonzero if anything failed.
        # CONFIG_SHELL comes from the CI profile; fall back to PATH lookup so
        # the same recipe also runs outside the hnp environment.
        shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "bash"
        self.run(f"{shell} test.sh ./spigot", env="conanbuild")

    def package(self):
        autotools = Autotools(self)
        # Installs bin/spigot + share/man/man1/spigot.1 + share/doc/spigot/spigot.html
        autotools.install()

    def package_info(self):
        # Standalone executable; GMP and ncurses are linked in statically, so the
        # only dynamic dependency left is the platform libc.so.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
