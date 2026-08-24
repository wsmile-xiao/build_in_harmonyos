#!/usr/bin/env python3
"""Conan recipe for ghostscript 10.07.1 — PostScript/PDF interpreter and renderer.

Ghostscript is a PostScript and PDF interpreter, renderer, and converter.
Build system: autotools (custom configure + make).
Bundles its own third-party libraries (zlib, libpng, jpeg, tiff, freetype, etc.)
No external conan dependencies required.

Patches:
  0001: Main config.guess — HarmonyOS detection
  0002: configure — umask 077→022 for HMDFS compatibility
  0003-0007: Sub-project config.guess files (ijs, jpeg, lcms2mt, libpng, tiff)

Packaged as an application (gs binary), not a library.
"""

import json
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GhostscriptConan(ConanFile):
    name = "ghostscript"
    version = "10.07.1"
    description = "Ghostscript — PostScript/PDF interpreter and renderer"
    license = "AGPL-3.0-only"
    homepage = "https://www.ghostscript.com/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _build_root(self):
        """Return tmpfs build directory to avoid HMDFS permission issues."""
        return "/data/storage/el2/base/.conan-build-ghostscript-10.07.1"

    def build(self):
        apply_conandata_patches(self)

        root = self._build_root()
        work = os.path.join(root, "src")
        install_dir = os.path.join(root, "install")
        tmpdir = os.path.join(root, "tmp")

        # Clean and create tmpfs directories
        if os.path.isdir(work):
            shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work, exist_ok=True)
        os.makedirs(install_dir, exist_ok=True)
        os.makedirs(tmpdir, exist_ok=True)

        # Copy patched sources to tmpfs
        self.run(f'cp -a "{self.source_folder}/." "{work}/"')

        # Build environment from conan profile
        # R33: compiler from Conan conf (self.conf.get), not bare shell vars.
        # self.conf_info is for SETTING conf in package_info(); in build() use self.conf.get().
        # Profile may supply the value as a JSON string or already-parsed dict — handle both.
        compiler_executables = self.conf.get("tools.build:compiler_executables", {})
        if isinstance(compiler_executables, str):
            try:
                compiler_executables = json.loads(compiler_executables)
            except (json.JSONDecodeError, TypeError):
                compiler_executables = {}
        if not isinstance(compiler_executables, dict):
            compiler_executables = {}

        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        cc = compiler_executables.get("c", "/data/service/hnp/bin/clang")
        cxx = compiler_executables.get("cpp", "/data/service/hnp/bin/clang++")

        env = (
            f"CC={cc} CXX={cxx}"
            f" TMPDIR={tmpdir}"
            f" CONFIG_SHELL={bash}"
            f" SHELL={bash}"
        )

        # Configure
        self.run(
            f'{bash} -c \'cd {work} && export {env}'
            f' && ./configure --prefix={install_dir}\''
        )

        # Build (ghostscript is memory-intensive, use -j1)
        self.run(f'{bash} -c \'cd {work} && export {env} && make -j1\'')

        # Install
        self.run(f'{bash} -c \'cd {work} && export {env} && make install\'')

        self._install_dir = install_dir

    def package(self):
        install_dir = getattr(self, "_install_dir", None)
        if install_dir is None:
            return

        # Copy bin/
        src_bin = os.path.join(install_dir, "bin")
        if os.path.isdir(src_bin):
            shutil.copytree(
                src_bin, os.path.join(self.package_folder, "bin"), dirs_exist_ok=True
            )

        # Copy lib/
        src_lib = os.path.join(install_dir, "lib")
        if os.path.isdir(src_lib):
            shutil.copytree(
                src_lib, os.path.join(self.package_folder, "lib"), dirs_exist_ok=True
            )

        # Copy include/
        src_include = os.path.join(install_dir, "include")
        if os.path.isdir(src_include):
            shutil.copytree(
                src_include,
                os.path.join(self.package_folder, "include"),
                dirs_exist_ok=True,
            )

        # Copy share/ghostscript/ (resources, fonts, etc.)
        src_share = os.path.join(install_dir, "share")
        if os.path.isdir(src_share):
            shutil.copytree(
                src_share,
                os.path.join(self.package_folder, "share"),
                dirs_exist_ok=True,
            )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
