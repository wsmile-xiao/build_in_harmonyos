#!/usr/bin/env python3
"""Conan recipe for BoolStuff 0.1.16 on HarmonyOS (OHOS).

BoolStuff is a small C++ library operating on boolean expression binary
trees (parsing and Disjunctive Normal Form) with the `booldnf` command-line
tool.  Upstream builds with autoconf/automake/libtool and has no third-party
dependencies.

OHOS-specific handling (evidence in notes.md):
- explicit --build/--host triplet (2016 config.guess cannot guess HarmonyOS)
- Latin-1 -> UTF-8 and umask patches (patches/0001-ohos-autotools-compat.patch)
- C++17 noexcept patch (patches/0002-cpp17-noexcept.patch)
- configure runs under CONFIG_SHELL=/bin/sh via a command-line prefix
  assignment (profile buildenv CONFIG_SHELL=bash corrupts generated libtool)
- autotools dependency-chain timestamps pinned so the maintainer rules never
  regenerate configure and wipe the patches
"""

import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    rm,
    rmdir,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class BoolstuffConan(ConanFile):
    name = "boolstuff"
    version = "0.1.16"
    description = (
        "C++ library operating on boolean expression binary trees "
        "(parsing and Disjunctive Normal Form), with the booldnf command-line tool"
    )
    license = "GPL-2.0-or-later"
    homepage = "http://sarrazip.com/dev/boolstuff.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("boolean", "expression", "parser", "dnf", "logic")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # boolstuff is self-contained: no third-party dependencies (upstream README/INSTALL).
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # The 2016 config.guess shipped upstream cannot recognize
        # "aarch64-HarmonyOS" (uname -s = HarmonyOS) and aborts with
        # "cannot guess build type".  The OHOS device builds natively, so
        # an explicit build/host triplet identical to the host makes
        # configure skip config.guess entirely while keeping the
        # Linux-compatible code paths used by the OHOS userland.
        # (Recorded on the toolchain for traceability; build() passes the
        # same values explicitly because configure is invoked manually.)
        arch = str(self.settings.arch)
        cpu = "aarch64" if arch in ("armv8", "aarch64") else arch
        triplet = f"{cpu}-unknown-linux-gnu"
        tc.generate()
        # Keep the C locale so sed/awk inside configure and config.status
        # compare bytes instead of locale-collated characters on OHOS.
        # (CONFIG_SHELL is pinned to /bin/sh inside build() with a command
        # line prefix assignment; see the note there.)
        env = Environment()
        env.define("LC_ALL", "C")
        env.vars(self).save_script("boolstuff-build-env")

    def _libtool_link_switches(self):
        # Map the Conan shared option onto the libtool switches.  Upstream
        # configures libtool with AC_DISABLE_STATIC (shared default).
        if self.options.shared:
            return "--enable-shared --disable-static"
        return "--enable-static --disable-shared"

    def build(self):
        apply_conandata_patches(self)
        self._pin_autotools_timestamps()
        autotools = Autotools(self)
        # Run configure with an in-command CONFIG_SHELL assignment: the
        # aggregated conanbuild env (profile buildenv) sets CONFIG_SHELL to
        # bash and wins over recipe env scripts, but a command-line prefix
        # assignment always does.  Under bash the libtool generated from
        # ltmain.sh 2.4.2 loses quote escaping (archive_expsym_cmds) and
        # dies with a syntax error near `}'; under /bin/sh the full
        # configure->libtool->make chain was verified on the device.
        # Flags mirror AutotoolsToolchain defaults (prefix=/, bindir layout).
        arch = str(self.settings.arch)
        cpu = "aarch64" if arch in ("armv8", "aarch64") else arch
        triplet = f"{cpu}-unknown-linux-gnu"
        self.run(
            f"CONFIG_SHELL=/bin/sh {self.source_folder}/configure "
            f"--build={triplet} --host={triplet} "
            f"{self._libtool_link_switches()} "
            "--prefix=/ "
            "'--bindir=${prefix}/bin' "
            "'--sbindir=${prefix}/bin' "
            "'--libdir=${prefix}/lib' "
            "'--includedir=${prefix}/include' "
            "'--oldincludedir=${prefix}/include'"
        )
        autotools.make(args=["-j1"])
        # Upstream test suites (src/boolstuff and src/commands "check" targets):
        #   - checkdnf + check-test-cases.pl over test-cases.txt (52 cases)
        #   - checkc (C API assertion program)
        #   - booldnf --version/--help/--unknown/stdin behavior assertions
        #   - test-regressions.pl over regressions.txt (60 cases)
        autotools.make(target="check")

    def _pin_autotools_timestamps(self):
        # The patches rewrite configure/configure.ac, which makes them look
        # newer than the shipped aclocal.m4/Makefile.in.  The automake
        # maintainer rules would then re-run aclocal/automake/autoconf
        # through missing(1); on an OHOS device that picks up a mismatched
        # system autoconf and regenerates configure WITHOUT the patches
        # (including the umask fix), breaking config.status.  Pin every file
        # participating in the autotools dependency chain (inputs, macros and
        # generated products, at any depth) to one identical timestamp: GNU
        # make treats equal mtimes as up to date, so no regeneration fires.
        stamp = 978307200  # 2001-01-01, older than any real input edit
        src = self.source_folder
        keep = (".m4", ".am", ".in", ".ac")
        keep_exact = ("configure", "config.guess", "config.sub", "ltmain.sh",
                      "compile", "depcomp", "missing", "install-sh",
                      "mkinstalldirs", "aclocal.m4", "config.h.in")
        for root, _dirs, files in os.walk(src):
            for name in files:
                if name.endswith(keep) or name in keep_exact:
                    os.utime(os.path.join(root, name), (stamp, stamp))

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # libtool leftovers are never shipped.
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        rm(self, "*.dylib", os.path.join(self.package_folder, "lib"), recursive=True)
        # boolstuff is not a system-renamed library on OHOS: keep the .so.
        # Drop standalone man/doc trees to keep the package minimal.
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        # Headers are installed under include/boolstuff-0.1/boolstuff/ and the
        # upstream pkg-config file uses -I${includedir}/boolstuff-0.1, so the
        # consumers #include <boolstuff/BoolExprParser.h>.
        self.cpp_info.includedirs = [os.path.join("include", "boolstuff-0.1")]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["boolstuff-0.1"]
        # booldnf command-line tool shipped in the same package.
        self.buildenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
