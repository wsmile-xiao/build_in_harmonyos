#!/usr/bin/env python3
"""Conan recipe for icoutils 0.32.3 — Windows icon/cursor extraction tools."""

import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout


class IcoutilsConan(ConanFile):
    name = "icoutils"
    version = "0.32.3"
    description = "Extract and convert Windows icon and cursor resources (ICO/CUR/ANI)"
    license = "GPL-3.0"
    homepage = "https://www.nongnu.org/icoutil/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "config.guess", os.path.join(self.recipe_folder, "patches"),
             os.path.join(self.export_sources_folder, "patches"))
        copy(self, "config.sub", os.path.join(self.recipe_folder, "patches"),
             os.path.join(self.export_sources_folder, "patches"))

    def requirements(self):
        self.requires("libpng/1.6.58.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Copy OHOS-aware config.guess/config.sub to source
        for fname in ("config.guess", "config.sub"):
            src = os.path.join(self.export_sources_folder, "patches", fname)
            dst = os.path.join(self.source_folder, "build-aux", fname)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
                os.chmod(dst, 0o755)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

    def build(self):
        # Replace config.guess/config.sub with OHOS-aware versions
        for fname in ("config.guess", "config.sub"):
            src = os.path.join(self.recipe_folder, "patches", fname)
            dst = os.path.join(self.source_folder, "build-aux", fname)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
                os.chmod(dst, 0o755)

        # Also relax umask in config.guess (same HMDFS issue as configure)
        config_guess = Path(self.source_folder, "build-aux", "config.guess")
        if config_guess.is_file():
            self._relax_private_umask(config_guess)

        apply_conandata_patches(self)

        # Always use the posix shell approach with proper --build/--host
        # to handle both native OHOS and CI cross-compilation
        self._configure_with_posix_shell()
        self._run_with_posix_shell("make -j1")

    def package(self):
        if str(self.settings.os) == "OHOS":
            destination = shlex.quote(self.package_folder)
            self._run_with_posix_shell(
                "make -j1 install DESTDIR=" + destination
            )
        else:
            autotools = Autotools(self)
            autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    def _configure_with_posix_shell(self):
        compiler = self._c_compiler()

        configure = Path(self.source_folder, "configure")
        temp_configure = Path(self.build_folder, ".conan-configure")
        shutil.copy2(configure, temp_configure)
        self._relax_private_umask(temp_configure)

        # Get triplet from compiler (config.guess doesn't work on all HMDFS)
        triplet = subprocess.check_output(
            [compiler, "-dumpmachine"], text=True
        ).strip()
        if not triplet:
            raise ConanInvalidConfiguration("C compiler returned an empty target triplet")

        tc = AutotoolsToolchain(self)
        arguments = list(tc.configure_args)
        arguments.append("--build=" + triplet)
        arguments.append("--host=" + triplet)
        arguments.append("--srcdir=" + self.source_folder)

        command = "{} {}".format(
            shlex.quote(str(temp_configure)),
            " ".join(shlex.quote(a) for a in arguments),
        )
        self._run_with_posix_shell(command)

    def _run_with_posix_shell(self, command):
        shell = shlex.quote(self._posix_shell())
        # Clear LIBS during configure: AutotoolsDeps sets LIBS=-lpng16 -lm
        # which causes AC_PROG_CC's cross-compilation check to link the test
        # binary against libpng16, which then can't be found at runtime.
        # AC_CHECK_LIB will add -lpng itself later in the configure run.
        prefix = "export SHELL=" + shell + " CONFIG_SHELL=" + shell + " LIBS=; "
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")

    def _posix_shell(self):
        shell = "/system/bin/sh" if os.path.isfile("/system/bin/sh") else shutil.which("sh")
        if not shell:
            raise ConanInvalidConfiguration("No POSIX shell is available")
        return shell

    def _c_compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = executables.get("c") or shutil.which("cc")
        if not compiler:
            raise ConanInvalidConfiguration("No C compiler is configured")
        return compiler

    @staticmethod
    def _relax_private_umask(configure):
        path = Path(configure)
        content = path.read_text(encoding="utf-8", errors="surrogateescape")
        content = content.replace("umask 077", "umask 022")
        path.write_text(content, encoding="utf-8", errors="surrogateescape")
