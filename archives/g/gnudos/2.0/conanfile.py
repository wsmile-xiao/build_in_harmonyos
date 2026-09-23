#!/usr/bin/env python3
"""Conan recipe — gnudos 2.0

GNU DOS: a DOS-style file manager suite for the console (mino editor and
prime file manager, both ncurses TUIs, built on src/corelib).
Build system: Autotools (release tarball ships configure).
License: GPL-3.0-or-later.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GnudosConan(ConanFile):
    name = "gnudos"
    version = "2.0"
    description = "GNU DOS - DOS-style console file manager suite (mino editor, prime file manager)"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/gnudos/"
    url = "https://www.gnu.org/software/gnudos/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            # old config.guess/sub can't guess on OHOS and reject new triplets
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            # E386 family: the profile buildenv points CONFIG_SHELL at the hnp
            # bash, whose getcwd() always fails on HMDFS build dirs.  Route
            # autoconf and make to the system /bin/sh.
            env = Environment()
            env.define("CONFIG_SHELL", "/bin/sh")
            env.define("SHELL", "/bin/sh")
            tc.generate(env=env)
        else:
            tc.generate()
        # ncurses/6.6 dependency flags (CPPFLAGS/LDFLAGS/LIBS) must reach
        # configure's `library containing initscr` probe via conanbuild env.
        AutotoolsDeps(self).generate()
        tc.configure_args.append(f"--prefix={self.package_folder}")
        # config.status depfiles bootstrap is fragile on CI workers
        # ("Something went wrong bootstrapping makefile fragments");
        # automatic dependency tracking buys nothing for a package build.
        tc.configure_args.append("--disable-dependency-tracking")
        # Quote args containing ${...} verbatim: unquoted, the shell expands
        # ${prefix} to empty at command time and install paths become /lib.
        def _q(a):
            return f"'{a}'" if "$" in a else (f'"{a}"' if " " in a else a)
        self._configure_args = " ".join(_q(a) for a in tc.configure_args)

    def build(self):
        apply_conandata_patches(self)
        # E011: HMDFS + umask 077 in shipped configure breaks config.status
        import glob
        for _cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
            with open(_cfg, encoding="utf-8", errors="ignore") as f:
                text = f.read()
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        # E386/§12.38②: the conan cache build subdir itself triggers getcwd
        # storms on HMDFS even with a safe shell, so configure/make in-source:
        # the subprocess starts from the healthy worktree cwd and the shell cd
        # into the source tree internally (PWD-based, no system getcwd()).
        src = self.source_folder
        # MKDIR_P/INSTALL: configure would otherwise burn user-local shim
        # scripts (~/usr/local/bin/...) into the Makefile as absolute paths;
        # CI workers lack those shims' dependencies (curl) and die with 127.
        # Use plain PATH-resolved mkdir and the tree's bundled install-sh.
        self.run(
            f'cd "{src}" && env CONFIG_SHELL=/bin/sh SHELL=/bin/sh '
            f'./configure {self._configure_args} && make -j1 '
            f'MKDIR_P="mkdir -p" INSTALL="./install-sh -c"',
            env="conanbuild")

    def package(self):
        src = self.source_folder
        # The 2.0 tarball ships install-sh without the exec bit and conan's
        # source copy preserves it; libtool execs INSTALL directly and would
        # fail with EACCES.
        for _helper in ("install-sh", "missing", "depcomp", "compile"):
            _p = os.path.join(src, _helper)
            if os.path.exists(_p):
                os.chmod(_p, 0o755)
        self.run(
            f'cd "{src}" && env CONFIG_SHELL=/bin/sh SHELL=/bin/sh make install '
            f'MKDIR_P="mkdir -p" INSTALL="{src}/install-sh -c"',
            env="conanbuild")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
