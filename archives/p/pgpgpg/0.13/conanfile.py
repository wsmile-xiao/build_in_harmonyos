#!/usr/bin/env python3
"""Conan recipe for pgpgpg 0.13.

pgpgpg is a PGP 2.6.x compatible front end for GnuPG: it parses PGP style
command line options, translates them into gpg options and then executes
gpg.  The upstream release tarball already ships ``configure`` and
``Makefile.in``, so the HarmonyOS device never regenerates Autotools files.

Why configure has to be pointed at a concrete gpg binary:

* ``configure.in:21`` declares ``--with-gpg-path=PATH``; ``:40`` rejects a
  relative path, ``:47`` rejects a non-executable file, ``:57`` falls back to
  ``AC_PATH_PROG``, ``:58-67`` abort the build when no gpg is reachable, and
  ``:69`` stores the value via ``AC_DEFINE_UNQUOTED(GPG_PATH, "$path_to_gpg")``.
* ``pgpopts.c:725`` and ``defaultkey.c:54`` use that macro as ``argv[0]`` and
  ``main.c:147`` runs ``execv(gpg_argv[0], gpg_argv)``.  ``execv`` does not
  search ``PATH``, so a bare ``gpg`` name can never work; the absolute path is
  frozen into the shipped binary at configure time.

gnupg is therefore consumed as an executed external program
(``tool_requires``) rather than as a link-time library, and its Conan package
folder provides the absolute path.  The resulting "cache path is baked in"
limitation is documented in notes.md.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PgpgpgConan(ConanFile):
    name = "pgpgpg"
    version = "0.13"
    description = "Wrapper around GnuPG that accepts PGP 2.6 command line options"
    license = "GPL-2.0-or-later"
    homepage = "https://mroth.net/pgpgpg/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("pgpgpg is supported only on Linux and OHOS")
        if str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration("pgpgpg is packaged for the aarch64 target")

    def build_requirements(self):
        # pgpgpg execs gpg; it never links against it.  The configure probe
        # demands an executable absolute path, which the Conan package folder
        # of gnupg provides.
        self.tool_requires("gnupg/2.4.9.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # tool_requires live in the build context: self.dependencies["gnupg"]
        # raises KeyError "'gnupg' not found in the dependency set" (that
        # accessor defaults to the host context).  Use the documented build
        # view, same as archives/a/abx/0.1/conanfile.py:166 does for automake.
        gnupg = self.dependencies.build["gnupg"].package_folder
        gpg = os.path.join(gnupg, "bin", "gpg")
        tc.configure_args.append("--with-gpg-path=" + gpg)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream registers no tests at all (grep -n TESTS Makefile.in finds
        # nothing and Makefile.in:285 check-am: all-am is a no-op), so this is
        # only an install-surface smoke run.  It is deliberately NOT counted as
        # upstream test integration: see upstream_test_in_build in
        # test_package/MANIFEST.yml.
        autotools.make(target="check")

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
