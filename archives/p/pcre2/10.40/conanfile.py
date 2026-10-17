#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Pcre2, pcre2, 10.40, Perl Compatible Regular Expressions library (version 2, current), BSD-3-Clause, https://www.pcre.org/
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Pcre2Conan(ConanFile):
    name = "pcre2"
    version = "10.40"
    description = "Perl Compatible Regular Expressions library (version 2, current)"
    license = "BSD-3-Clause"
    homepage = "https://www.pcre.org/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # Try GitHub URL first; fall back to local tarball if network unavailable
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
        except Exception:
            local_tarball = os.path.join(
                os.path.expanduser("~"), "tmp", "builds", "pcre2-10.40.tar.gz"
            )
            if os.path.exists(local_tarball):
                get(self, f"file://{local_tarball}", sha256=self.conan_data["sources"]["sha256"], strip_root=True)
            else:
                raise

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
        # ncurses: tc.configure_args.append("--without-shared")  # R4
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix HMDFS umask 077 issue: config.status creates temp dirs with umask 077
        # which prevents file creation inside on HMDFS. Change to umask 022 and
        # use a writable temp directory instead of current dir.
        if self.settings.os in ("Linux", "OHOS"):
            for fn in ["configure"]:
                path = os.path.join(self.source_folder, fn)
                if os.path.isfile(path):
                    with open(path, "r") as f:
                        content = f.read()
                    content = content.replace("umask 077", "umask 022")
                    tmpdir = os.environ.get("TMPDIR", "/tmp")
                    content = content.replace(
                        'mktemp -d "./confXXXXXX"',
                        f'mktemp -d "{tmpdir}/confXXXXXX"'
                    )
                    with open(path, "w") as f:
                        f.write(content)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["pcre2-8", "pcre2-posix"]
