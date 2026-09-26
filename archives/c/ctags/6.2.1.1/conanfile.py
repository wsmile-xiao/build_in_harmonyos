#!/usr/bin/env python3
"""Conan recipe — ctags 6.2.1 (Universal Ctags).

Universal Ctags is an autotools project.  The official release tarball
already ships a pre-generated ``configure``, so ``autoreconf`` is not
needed.

OpenHarmony adaptations (see patches/):

* ``0001-config.guess.patch`` — teach ``config.guess`` about HarmonyOS.
  ``uname -s`` reports ``HarmonyOS`` instead of ``Linux``, so the script
  is unable to guess a build triple and ``configure`` aborts with
  ``cannot guess build type; you must specify one``.  The patch maps the
  reported machine to ``<machine>-unknown-linux-ohos``.
* ``0002-configure.patch`` — create the ``config.status`` temporary
  directory with ``mkdir`` instead of ``mktemp -d``.  On HMDFS the
  directory returned by toybox ``mktemp -d`` is created ``0700`` and
  owned by the filesystem service account, so the calling user cannot
  write into it; ``chmod`` is a no-op on HMDFS and ``test -w`` wrongly
  reports the directory as writable.
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CtagsConan(ConanFile):
    name = "ctags"
    version = "6.2.1.1"
    description = "Universal Ctags - a multilanguage code indexing tool"
    license = "MIT"
    homepage = "https://ctags.io/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No mandatory third-party dependencies.  libxml2, jansson,
        # libseccomp, libyaml and libpcre2 are all optional: configure
        # detects them and simply disables the corresponding features.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # ctags is a standalone terminal tool: link it statically so the
        # produced executables do not pick up shared libraries at runtime.
        tc.extra_ldflags.append("-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Terminal tool: only executables are provided, no libraries.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
