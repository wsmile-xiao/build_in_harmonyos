#!/usr/bin/env python3
"""Conan recipe for riece 9.0.0 — an IRC client for Emacs.

riece is a pure Emacs Lisp add-on package: there is no C/C++ code to compile.
The build is the Emacs byte-compilation driven by the upstream autotools
wrapper (configure + make), and the upstream test-suite is ``make check``
(lisp/test/*.el executed through the lunit framework).
"""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class RieceConan(ConanFile):
    name = "riece"
    version = "9.0.0"
    description = "Riece is an IRC client for Emacs (pure Emacs Lisp package)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.nongnu.org/riece/"
    url = "https://download.savannah.nongnu.org/releases/riece/"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("emacs/29.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"riece supports Linux and OHOS, got {self.settings.os}"
            )
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "riece is an architecture-independent Emacs Lisp package"
            )

    def package_id(self):
        # riece is architecture-independent Emacs Lisp.
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def _emacs(self):
        dependency = self.dependencies["emacs"]
        emacs = os.path.join(dependency.package_folder, "bin", "emacs")
        if not os.path.isfile(emacs):
            raise ConanInvalidConfiguration(f"Emacs executable is missing: {emacs}")
        return emacs

    def _configure_shell(self):
        if self.settings.os != "OHOS":
            return "sh"
        # Shell scripts living under the HMDFS home cannot be execve'd directly
        # by processes started from the home interpreter (knowledge draft
        # DRAFT-10038), so drive configure through a system-root shell.
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            "/data/service/hnp/bin/bash",
            "/system/bin/sh",
        ):
            if candidate and os.path.exists(candidate):
                return candidate
        return "sh"

    def generate(self):
        build_env = VirtualBuildEnv(self)
        if self.settings.os == "OHOS":
            # Emacs resolves external helpers (ls, true, ...) through its
            # exec-path, which is seeded from PATH.  On OHOS those coreutils
            # applets live in /system/bin; make sure it precedes /usr/bin,
            # whose toybox symlinks the build sandbox refuses to execve.
            build_env.environment().prepend_path("PATH", "/system/bin")
        build_env.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        emacs = shlex.quote(self._emacs())
        prefix = shlex.quote(self.package_folder)
        configure = shlex.quote(os.path.join(self.source_folder, "configure"))
        self.run(
            f"{self._configure_shell()} {configure} --prefix={prefix} EMACS={emacs}",
            cwd=self.source_folder,
            env="conanbuild",
        )
        # Byte-compile every module (lisp/Makefile ``all: elc``).
        self.run("make", cwd=self.source_folder, env="conanbuild")
        # Upstream test-suite: lisp/test/*.el driven by lunit through COMPILE.
        self.run("make check", cwd=self.source_folder, env="conanbuild")

    def package(self):
        # Drive the upstream ``riece-install`` helper directly through Emacs.
        # This is exactly what the lisp/Makefile ``install`` target runs, but it
        # avoids the automake install machinery, which shells out to the HMDFS
        # ``install-sh`` script that cannot be execve'd in this environment
        # (knowledge draft DRAFT-10038).
        emacs = shlex.quote(self._emacs())
        lisp_src = shlex.quote(os.path.join(self.source_folder, "lisp"))
        compile_el = shlex.quote(os.path.join(self.source_folder, "lisp", "COMPILE"))
        site_lisp = shlex.quote(
            os.path.join(self.package_folder, "share", "emacs", "site-lisp")
        )
        self.run(
            f"{emacs} -batch -q -no-site-file -l {compile_el} "
            f"-f riece-install {lisp_src} {site_lisp}",
            cwd=os.path.join(self.source_folder, "lisp"),
            env="conanbuild",
        )
        copy(
            self,
            "*.info",
            os.path.join(self.source_folder, "doc"),
            os.path.join(self.package_folder, "share", "info"),
            keep_path=False,
        )
        copy(
            self,
            "COPYING",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        lisp_dir = os.path.join(
            self.package_folder, "share", "emacs", "site-lisp", "riece"
        )
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.buildenv_info.define_path("RIECE_LISPDIR", lisp_dir)
        self.runenv_info.define_path("RIECE_LISPDIR", lisp_dir)
        self.buildenv_info.prepend_path("EMACSLOADPATH", lisp_dir)
        self.runenv_info.prepend_path("EMACSLOADPATH", lisp_dir)
