#!/usr/bin/env python3
"""Conan recipe — nsuds 0.7B (Ncurses Sudoku System).

nsuds is a text-graphical (ncurses) sudoku game written in C with autotools
(configure.ac + Makefile.am).  Upstream official git is on SourceForge; the
GitHub mirror jubalh/nsuds (master == 0.7B, commit 003eecf9) is used as the
archive source because SF serves an HTML page for the ci/tarball endpoint.

The git archive ships *no* pre-generated `configure` (autotools output is
never committed upstream), so build() bootstraps it with `autoreconf -fi`
(automake is provided as a conan tool_requires — the OHOS base image lacks
automake/aclocal, cf. afuse/abiword-plugin recipes).

OHOS adaptations:
  * ncurses comes from the conan ncurses/6.6 package (static wide-char build,
    R26: never install a shared ncurses that would shadow the system lib).
    The package ships libncursesw.a only; nsuds' configure probes `-lncurses`,
    so a private alias libncurses.a -> libncursesw.a is created under the
    build folder (never touches /lib or /lib64).
  * The project is old ANSI-C code with tentative definitions in headers
    (level_data/showmarks in nsuds.h/grid.h); clang >= 11 defaults to
    -fno-common -> duplicate-symbol link errors.  -fcommon restores the
    historical behaviour.
  * `chgrp games` install hooks are dropped via a conandata patch (OHOS has
    no chgrp binary / no games group).  --disable-setgid avoids the setgid
    chmod 2555.
  * config.status uses `(umask 077 && mktemp -d ...)` which creates an
    unwritable drwx--S--- dir on HMDFS (E114); the umask is relaxed to 000
    after autoreconf, before configure runs.

No upstream test suite exists (no TESTS, `make check` is a no-op), so the
verifiable non-interactive CLI paths (--version/-v/--help/-h) are exercised
by test_package/test.sh.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NsudsConan(ConanFile):
    name = "nsuds"
    # Conan 2 requires lowercase recipe references; upstream version is 0.7B
    # (AC_INIT([nsuds], [0.7B])).  The lowercased "0.7b" keeps the reference
    # valid while the binary itself still reports "nsuds version 0.7B".
    version = "0.7b"
    description = "nsuds - The Ncurses Sudoku System (text-graphical sudoku game)"
    license = "GPL-2.0"
    homepage = "https://github.com/jubalh/nsuds"
    url = "https://github.com/jubalh/nsuds"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # Git archive ships no configure -> autoreconf bootstrap in build();
        # OHOS base image has no automake/aclocal (E178) so provide via conan.
        self.tool_requires("automake/1.18")

    def requirements(self):
        # R26: ncurses is a system-name library; the conan ncurses/6.6 package
        # is static-only (--without-shared), never shadowing /lib or /lib64.
        self.requires("ncurses/6.6")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"nsuds supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload GitHub commit URLs have no archive extension, so give get()
        # an explicit filename so the tar.gz is unpacked (not treated as zip).
        get(self, url=self.conan_data["sources"]["url"],
            sha256=self.conan_data["sources"]["sha256"],
            filename="nsuds-0.7b.tar.gz", strip_root=True)
        apply_conandata_patches(self)

    def _ncurses_prefix(self):
        return os.path.join(
            self.build_folder, "ncurses-alias"
        )

    def generate(self):
        nc = self.dependencies["ncurses"]
        nc_inc = os.path.join(nc.package_folder, "include")
        nc_lib = os.path.join(nc.package_folder, "lib")

        # Private alias lib so configure's AC_CHECK_LIB([ncurses]...) and the
        # final link (-lncurses) resolve against the wide-char static archive.
        alias_dir = os.path.join(self._ncurses_prefix(), "lib")
        os.makedirs(alias_dir, exist_ok=True)
        alias = os.path.join(alias_dir, "libncurses.a")
        if not os.path.lexists(alias):
            os.symlink(os.path.join(nc_lib, "libncursesw.a"), alias)

        tc = AutotoolsToolchain(self)
        # R33: compiler/flag injection via the toolchain (no bare shell env).
        tc.extra_cflags.append("-fcommon")          # tentative-definition C code
        tc.extra_cflags.append(f"-I{nc_inc}")
        tc.extra_ldflags.append(f"-L{alias_dir} -L{nc_lib}")
        tc.configure_args.extend(["--disable-setgid", "--prefix=/"])
        tc.generate()

    def build(self):
        # Bootstrap the configure script (git archive ships configure.ac only).
        self.run("autoreconf --install --verbose", cwd=self.source_folder)
        # E114: HMDFS turns `umask 077 && mktemp -d` temp dirs into unwritable
        # drwx--S--- dirs; relax before configure (config.status inherits it).
        self.run("sed -i 's/umask 077/umask 000/g' configure",
                 cwd=self.source_folder)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Pure command-line tool: no library to link against.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        # Make the binary reachable for consumers / test_package (conanrun).
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
