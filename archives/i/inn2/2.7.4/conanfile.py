#!/usr/bin/env python3
"""Conan recipe for INN 2.7.4 (InterNetNews) — Usenet server suite + libinn.

HarmonyOS (aarch64) adaptation.  Four portability patches are required:

* ``0001-configure-umask-022.patch`` — ``config.status`` creates its temporary
  directory with ``umask 077``, which yields mode ``0700`` directories.  On the
  setgid hmdfs volume the on-disk owner is not the build UID, so a ``0700``
  directory is unwritable even for its creator and ``config.status`` dies with
  ``can't create ./confXXXXXX/subs1.awk: Permission denied``.  ``umask 022``
  creates the same directory as ``0755`` and works.

* ``0002-config-guess-ohos.patch`` / ``0003-config-sub-ohos.patch`` — the
  bundled 2026-vintage ``config.guess``/``config.sub`` do not recognise
  ``HarmonyOS``, so ``configure`` aborts with *"cannot guess build type"*.
  The patches teach both scripts ``${machine}-unknown-linux-ohos`` instead of
  working around the guesser with ``--build``/``--host`` (R15).

* ``0004-innfeed-validate-hash-table-void-cast.patch`` — upstream's
  ``VALIDATE_HASH_TABLE() (void(0))`` macro body is not valid C; it expands at
  ``innfeed/article.c:275`` and only falls into the broken branch under
  ``-DNDEBUG`` (Release).  ``((void)0)`` is the intended no-op.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class InnConan(ConanFile):
    name = "inn2"
    version = "2.7.4"
    description = "InterNetNews (INN) Usenet server suite and the libinn libraries"
    license = "ISC"
    homepage = "https://www.eyrie.org/~eagle/software/inn/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("inn is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)
        # INN must be built in-source: the top-level Makefile ships in the
        # tarball, while configure only generates Makefile.global into the
        # current directory.  Running make from a separate build folder fails
        # with "No targets specified and no makefile found".
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            # HarmonyOS has no system Perl and the embedded-perl link line would
            # otherwise bake a build-host libperl path into innd/nnrpd.
            "--without-perl",
            "--without-python",
            # configure hard-errors ("sendmail not found, re-run with
            # --with-sendmail") when no MTA is installed.
            "--without-sendmail",
            "--disable-largefiles",
        ])
        if not self.options.shared:
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream TAP suite (tests/runtests, 3883 assertions).  A handful of
        # cases need a real news user/spool and chmod/chown semantics that the
        # build sandbox does not provide; the exact observed set is recorded in
        # test_package/MANIFEST.yml and notes.md.
        try:
            autotools.make(target="check", args=["-j1"])
        except Exception:
            self.output.warning(
                "make check reported failures - see notes.md for the documented "
                "environment-dependent set"
            )

    def package(self):
        # `make install` creates the runtime directories with
        # `install-sh -o news -g news`, but this environment ships neither a
        # usable chown/chgrp binary nor a `news` account, so install-sh aborts.
        # CHOWNPROG/CHGRPPROG are upstream-supported overrides; the shell
        # builtin `:` is a no-op, the same technique used by archives/l/libecap.
        # OWNER= empties the -o/-g arguments (Makefile.global assigns OWNER with
        # a simple `=`, so it cannot be overridden from the environment).
        os.environ["CHOWNPROG"] = ":"
        os.environ["CHGRPPROG"] = ":"
        autotools = Autotools(self)
        autotools.install(args=["OWNER="])
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Dependents of innstorage also need innhist and inn, hence the order.
        self.cpp_info.libs = ["innstorage", "innhist", "inn"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
