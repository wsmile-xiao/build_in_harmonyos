#!/usr/bin/env python3
"""Conan recipe for abnfgen 0.21.

The upstream release already contains configure and Makefile.in, so the
HarmonyOS device never has to regenerate Autotools files.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, load, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AbnfgenConan(ConanFile):
    name = "abnfgen"
    version = "0.21"
    description = "Generate random documents that match an ABNF grammar"
    license = "Custom permissive"
    homepage = "https://www.quut.com/abnfgen/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("abnfgen is supported only on Linux and OHOS")
        if str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration("abnfgen is packaged for the aarch64 target")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsToolchain(self).generate()

    def _patch_configure_mktemp(self, configure_path):
        """Patch the configure script so the config.status it emits uses
        ``mkdir`` instead of ``mktemp -d`` for its private temp dir.

        autotools' config.status creates a private temp dir via
        ``(umask 077 && mktemp -d "./confXXXXXX")``.  On HarmonyOS the
        Toybox ``mktemp -d`` creates the directory with mode ``2700``
        (``drwx--S---``) and the kernel then refuses ``open(O_WRONLY)``
        inside it, so ``echo 'BEGIN {' >"$ac_tmp/subs1.awk"`` aborts with
        ``Permission denied`` and ``configure`` dies with ``could not
        setup config files machinery``.  A restricted ``umask 077`` has
        the same result with ``mkdir`` on hmdfs: it inherits the parent
        directory's setgid bit as an uppercase ``S`` and remains unwritable.
        Plain ``mkdir`` instead produces an inherited ``drwxrws--x``
        directory that is writable, so replace the ``mktemp`` branch of the
        temp-dir dance with it.

        The replacement has to be made in ``configure`` itself (the
        template that ``configure`` writes verbatim into ``config.status``
        via ``cat >$CONFIG_STATUS``), before ``configure`` is invoked,
        because ``configure`` generates and immediately runs
        ``config.status`` in one shot.
        """
        contents = load(self, configure_path)
        old = 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n  test -d "$tmp"'
        new = 'tmp=./conf$$-$RANDOM && mkdir "$tmp"'
        if old not in contents:
            return
        contents = contents.replace(old, new)
        save(self, configure_path, contents)

    def build(self):
        apply_conandata_patches(self)
        configure_path = os.path.join(self.source_folder, "configure")
        self._patch_configure_mktemp(configure_path)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        autotools.make(target="check")

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
