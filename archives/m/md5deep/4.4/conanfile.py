#!/usr/bin/env python3
"""Conan recipe — md5deep 4.4 (hashdeep family of recursive hashing tools)."""

import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Md5deepConan(ConanFile):
    name = "md5deep"
    version = "4.4"
    description = ("Recursively compute and audit MD5/SHA-1/SHA-256/Tiger/"
                   "Whirlpool hashes of files (hashdeep/md5deep tool family)")
    license = "LicenseRef-public-domain AND GPL-2.0-only"  # bulk PD; Tiger code GPL-2.0
    homepage = "https://github.com/jessek/hashdeep"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # The upstream release asset for 4.4 is a Windows binary zip and the
        # git tag is a bare snapshot without a generated configure. CI workers
        # have no autoconf/automake, so the pre-generated autotools files
        # (configure, Makefile.in, config.h.in, aclocal.m4 + modern
        # config.guess/config.sub) are shipped here and extracted in build().
        copy(self, "prebuilt.tar.gz",
             src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        # Self-contained: bundles its own MD5/SHA/Tiger/Whirlpool code, only
        # needs libc + pthread (part of musl on OHOS).
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # OHOS has no /bin/sh; configure must run under bash.
        if self.settings.os in ("Linux", "OHOS"):
            tc.configure_args.append("SHELL=/data/service/hnp/bin/bash")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # Overlay the pre-generated autotools build system onto the snapshot.
        self.run("tar xzf {} -C {}".format(
            os.path.join(self.source_folder, "prebuilt.tar.gz"), src))
        if self.settings.os in ("Linux", "OHOS"):
            # OHOS: no /bin/sh — rewrite shebangs to bash.
            for f in ["configure", "config.sub",
                      "install-sh", "missing", "compile", "depcomp"]:
                path = os.path.join(src, f)
                if os.path.exists(path):
                    self.run("sed -i '1s|^#!.*|#!/data/service/hnp/bin/bash|' "
                             + path)
            # HMDFS blocks writing into 0700 temp dirs, breaking configure's
            # temp-file creation. Drop umask 077.
            self.run("sed -i 's|umask 077 && mktemp|mktemp|g; "
                     "s|umask 077 && mkdir|mkdir|g' configure", cwd=src)
        if self.settings.os == "OHOS":
            # E007: the OHOS worker reports `uname -s = HarmonyOS`, which
            # config.guess (2021) can't recognize -> "cannot guess build type".
            # This is a native build (conan sets host==build, no --host, so
            # cross_compiling stays no) and configure.ac only distinguishes
            # *linux* vs mingw, so pin config.guess to the canonical OHOS triple
            # (arch is fixed aarch64) and teach config.sub to accept linux-ohos.
            self.run("printf '#!/data/service/hnp/bin/bash\\necho "
                     "aarch64-unknown-linux-ohos\\n' > config.guess", cwd=src)
            self.run("sed -i 's#gnu\\* | android\\*#gnu* | ohos* | android*#' "
                     "config.sub", cwd=src)
            self.run("sed -i 's#linux-musl\\* | linux-relibc\\*#linux-musl* | "
                     "linux-ohos* | linux-relibc*#' config.sub", cwd=src)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
