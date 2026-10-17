#!/usr/bin/env python3
"""Conan recipe — fontopia 2.0 (Autotools console font editor).

Fontopia is the GNU console font editor: an ncurses TUI built on top of the
GnuDOS console library. `configure.ac` hard-requires the GnuDOS headers
(console/dialogs.h, console/kbd.h, console/screen.h) and upstream
Makefile.am links `-lgnudos`, so the only dependency is `gnudos/2.0`
(ncurses comes transitively from it).

OHOS notes:
  - E386/§12.38②: configure/make run with CONFIG_SHELL/SHELL=/bin/sh and
    in-source. The profile buildenv points those at the hnp bash, whose
    getcwd() fails on HMDFS build dirs; running from the (healthy) worktree
    cwd with the shell doing the internal `cd` avoids the getcwd storms.
  - E011: the shipped `configure` wraps its temporary directories in
    `umask 077`, which breaks config.status on HMDFS; normalized to 022.
  - R33: the compiler comes from the Conan profile; gnudos/ncurses
    include/lib flags are provided by AutotoolsDeps (conanbuild env).
  - The upstream tarball ships no test suite (no check/test target and no
    test sources), so the deliverable is verified by test_package/ driving
    the installed binary (R34/R51).
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class FontopiaConan(ConanFile):
    name = "fontopia"
    version = "2.0"
    description = ("GNU Fontopia - console font editor (ncurses TUI built on the "
                   "GnuDOS console library)")
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/fontopia/"
    url = "https://www.gnu.org/software/fontopia/"
    topics = ("font", "console", "ncurses", "tui", "editor")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac requires console/{dialogs,kbd,screen}.h and
        # Makefile.am links -lgnudos; both come from GnuDOS. The ncurses
        # headers/libs must be declared explicitly: gnudos is packaged as an
        # application, and Conan 2 does not propagate an application's own
        # requirements to its consumers (so <ncurses.h> would be missing).
        self.requires("gnudos/2.0")
        self.requires("ncurses/6.6")

    def validate(self):
        # R32: OHOS must be matched alongside Linux.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append(f"--prefix={self.package_folder}")
        # config.status depfiles bootstrap is fragile on CI workers.
        tc.configure_args.append("--disable-dependency-tracking")
        env = Environment()
        if self.settings.os == "OHOS":
            # old config.guess/sub cannot guess OHOS and reject the new triplet
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            env.define("CONFIG_SHELL", "/bin/sh")
            env.define("SHELL", "/bin/sh")
        tc.generate(env=env)
        # gnudos/ncurses CPPFLAGS/LDFLAGS/LIBS reach configure through the
        # conanbuild environment.
        AutotoolsDeps(self).generate()
        # gnudos 包里同时有 libgnudos.so 与 libgnudos.a，而设备链接器拒载该 .so
        # （未过 OHOS ELF 签名校验：运行时 "Error loading shared library
        #  libgnudos.so.2"；gnudos 自带的 mino/prime 正是静态链的，NEEDED 里没有
        #  它）。所以把上游 Makefile 的 `-lgnudos` 换成两个静态归档，消费者二进制
        # 只依赖 libc，不受他人包签名状态影响（ncurses/6.6 本身也只交付 .a）。
        _g = self.dependencies["gnudos"].package_folder
        _n = self.dependencies["ncurses"].package_folder
        self._ldadd_override = '"%s" "%s"' % (
            os.path.join(_g, "lib", "libgnudos.a"),
            os.path.join(_n, "lib", "libncursesw.a"))

        # Quote args containing ${...} verbatim: unquoted, the shell expands
        # ${prefix} to empty at command time and install paths become /lib.
        def _q(a):
            return f"'{a}'" if "$" in a else (f'"{a}"' if " " in a else a)

        self._configure_args = " ".join(_q(a) for a in tc.configure_args)

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # E011: HMDFS + umask 077 in the shipped configure breaks config.status.
        for _cfg in glob.glob(os.path.join(src, "**", "configure"), recursive=True):
            with open(_cfg, encoding="utf-8", errors="ignore") as f:
                text = f.read()
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        self.run(
            f'cd "{src}" && env CONFIG_SHELL=/bin/sh SHELL=/bin/sh '
            f'./configure {self._configure_args} && make -j1 '
            f'MKDIR_P="mkdir -p" INSTALL="./install-sh -c" '
            f"fontopia_LDADD='{self._ldadd_override}'",
            env="conanbuild")

    def package(self):
        src = self.source_folder
        # The release tarball ships install-sh without the exec bit; libtool
        # execs INSTALL directly and would die with EACCES.
        for _helper in ("install-sh", "missing", "depcomp", "compile"):
            _p = os.path.join(src, _helper)
            if os.path.exists(_p):
                os.chmod(_p, 0o755)
        self.run(
            f'cd "{src}" && env CONFIG_SHELL=/bin/sh SHELL=/bin/sh make install '
            f'MKDIR_P="mkdir -p" INSTALL="{src}/install-sh -c"',
            env="conanbuild")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
