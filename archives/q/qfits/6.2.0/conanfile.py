#!/usr/bin/env python3
"""Conan recipe for qfits 6.2.0 - FITS file access library and tools.

qfits is ESO's C library for reading/writing FITS files, shipped with the
command line tools dfits, dtfits, flipx, frameq, qextract and replacekey.

OHOS notes
----------
* Old (2007) autotools project; its shipped ``admin/config.sub`` (2004) does
  not know ``aarch64``.  The CI build host ships the autoconf suite under
  ``/data/service/hnp/bin`` but not ``aclocal``/``automake``, so
  ``automake``/``libtool`` are pulled in as ``tool_requires`` and
  ``autoreconf`` runs with ``env="conanbuild"`` so their ``bin`` is on PATH
  (same approach as abiword-plugin-*).  ``autoreconf -fi -I m4macros`` also
  picks up the project's own ``m4macros/`` macros.
* autoconf's generated ``configure``/``config.status`` create their scratch
  directory with ``umask 077 && mktemp -d``; on the OHOS shared filesystem
  (HMDFS, setgid parent) that yields an unwritable ``drwx--S---`` directory.
  Dropping ``umask 077`` fixes it (E114 / DRAFT-6507).
* The device ``uname()`` reports ``HarmonyOS``, which ``config.guess`` cannot
  map to a triplet, so ``--build=aarch64-unknown-linux-ohos`` is passed.
* ``make install`` only installs ``qfits.h`` while it includes the other
  ``qfits_*.h`` headers, so the remaining headers are installed as well.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, rm)
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


class QfitsConan(ConanFile):
    name = "qfits"
    version = "6.2.0"
    description = "ESO FITS file access library and tools"
    license = "GPL-2.0-or-later"
    homepage = "https://www.eso.org/sci/software/eclipse/qfits/"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # The shipped config.sub (2004) cannot know aarch64 and the build host
        # lacks automake/aclocal; pull them in as tool_requires.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "qfits OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

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
        cxx = self._compiler("cpp", "clang++")
        # Regenerate configure/config.sub from configure.ac with the host's
        # modern autotools (-I m4macros for ESO_CHECK_*/QFITS_CHECK_*).
        self.run("autoreconf -fi -I m4macros", cwd=self.source_folder,
                 env="conanbuild")
        _drop_umask_077(os.path.join(self.source_folder, "configure"))
        shared = "--enable-shared" if self.options.shared else "--disable-shared"
        # config.guess cannot identify HarmonyOS; pass the triplet explicitly.
        self.run('CC="{}" CXX="{}" CPP="{} -E" ./configure '
                 '--build=aarch64-unknown-linux-ohos {} '
                 '--enable-static --prefix="{}"'.format(
                     cc, cxx, cc, shared, self.package_folder),
                 cwd=self.source_folder, env="conanbuild")
        # E074: parallel make hits the HMDFS jobserver fifo EPERM.
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")
        # Upstream test programs (self-contained, return 0 on success).
        self.run("make check", cwd=self.source_folder, env="conanbuild")

    def package(self):
        self.run("make install", cwd=self.source_folder, env="conanbuild")
        # Drop libtool archives (they embed absolute build paths).
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        # qfits.h includes the other qfits_*.h headers, which `make install`
        # does not install; add them so the public header is usable.
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["qfits"]
        if self.settings.os == "Linux":
            self.cpp_info.system_libs = ["m"]
