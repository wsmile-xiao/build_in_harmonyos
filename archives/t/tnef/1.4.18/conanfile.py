#!/usr/bin/env python3
"""Conan recipe for tnef 1.4.18 - TNEF (winmail.dat) decoder.

tnef decodes Microsoft's Transport Neutral Encapsulation Format (the
``winmail.dat`` attachment) and extracts the enclosed files.

OHOS notes
----------
* The Debian/upstream release tarball is a maintainer snapshot: it ships
  ``configure.ac``/``Makefile.am`` but **no generated ``configure``**.  The CI
  build host ships the autoconf suite under ``/data/service/hnp/bin`` but not
  ``aclocal``/``automake``, so ``automake``/``libtool`` are pulled in as
  ``tool_requires`` (same approach as abiword-plugin-* / argp-standalone) and
  ``autoreconf`` runs with ``env="conanbuild"`` so their ``bin`` is on PATH.
* The build is driven manually (in-source): the upstream ``tests/cmdline``
  baselines embed the relative path ``./../../src/tnef`` and only pass when
  srcdir == builddir.
* autoconf's generated ``configure``/``config.status`` create their scratch
  directory with ``umask 077 && mktemp -d``; on the OHOS shared filesystem
  (HMDFS, setgid parent) that yields an unwritable ``drwx--S---`` directory.
  Dropping ``umask 077`` fixes it (E114 / DRAFT-6507).
* ``AM_MAINTAINER_MODE`` keeps the maintainer rules disabled by default, so
  ``make`` will not try to re-run autotools during the build.
* The upstream ``tests/cmdline``/``tests/files`` suites are self-contained and
  are run with ``make check``.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.files import apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


def _prepare_autotools_env():
    """Point AUTOCONF/AUTOHEADER/AUTOM4TE/SED at whatever is on PATH: the
    tool_requires automake/autoconf wrappers may hardcode absolute paths."""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


def _drop_umask_077(path):
    """E114: HMDFS forces setgid on directories, so `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir that is not writable.  Remove `umask 077` so
    config.status can create its temp dir."""
    with open(path, "r", encoding="utf-8") as handle:
        data = handle.read()
    data = data.replace('(umask 077 && mktemp -d', '(mktemp -d')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(data)


class TnefConan(ConanFile):
    name = "tnef"
    version = "1.4.18"
    description = "Decode Microsoft TNEF (winmail.dat) attachments"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/verdammelt/tnef"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "tnef OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # The tarball has no generated configure and the build host lacks
        # automake/aclocal; pull them in as tool_requires (resolved with the
        # build profile, so conan create needs both -pr:h and -pr:b).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        _prepare_autotools_env()
        AutotoolsToolchain(self).generate()

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        _prepare_autotools_env()
        apply_conandata_patches(self)
        cc = self._compiler("c", "clang")
        # Regenerate configure from configure.ac (tarball ships none).
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        _drop_umask_077(os.path.join(self.source_folder, "configure"))
        # config.guess cannot identify HarmonyOS; pass the triplet explicitly.
        self.run('CC="{}" ./configure --build=aarch64-unknown-linux-ohos '
                 '--prefix="{}"'.format(cc, self.package_folder),
                 cwd=self.source_folder, env="conanbuild")
        # E074: parallel make hits the HMDFS jobserver fifo EPERM.
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")
        # Upstream self-contained command line test suites (29 .test scripts: 27 pass + 2 XFAIL).
        self.run("make check", cwd=self.source_folder, env="conanbuild")

    def package(self):
        copy(self, "tnef",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "tnef.1",
             src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
