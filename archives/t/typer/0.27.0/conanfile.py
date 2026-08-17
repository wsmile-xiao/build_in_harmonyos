#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for typer 0.27.0.

typer is a pure-Python CLI library. Its runtime dependencies
(`annotated-doc`, `shellingham`, `rich`) are not published as Conan
recipes in the OHOS artifact repository, so they are installed via pip
into the package folder and exposed through PYTHONPATH — the same
strategy used by buku/internetarchive.
"""

import os
import sys

from conan import ConanFile
from conan.tools.files import copy, get


# Pinned runtime dependencies. Versions follow typer's pyproject.toml
# lower bounds; pip resolves to the newest compatible release.
_RUNTIME_DEPS = (
    "annotated-doc>=0.0.2",
    "shellingham>=1.3.0",
    "rich>=13.8.0",
)


class TyperConan(ConanFile):
    name = "typer"
    version = "0.27.0"
    license = "MIT"
    author = "Sebastián Ramírez"
    url = "https://github.com/fastapi/typer"
    homepage = "https://typer.tiangolo.com/"
    description = "Typer, build great CLIs. Easy to code. Based on Python type hints."
    topics = ("cli", "python", "type-hints", "terminal")
    package_type = "library"
    # R32: L0p requires the full OHOS settings quartet even for
    # pure-Python packages; the extra settings are unused at build time.
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        # No patches currently, but keep the hook for future use.
        pass

    def configure(self):
        # Only the OS/arch matter for a pure-Python wheel.
        self.settings.rm_safe("os.version")

    def package_id(self):
        # Build is deterministic for pure-Python; collapse the id.
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        install_target = os.path.join(self.build_folder, "install")

        # Install runtime dependencies first (annotated-doc / shellingham /
        # rich are hard imports at the top of typer's modules).
        deps_target = os.path.join(self.build_folder, "deps")
        self.run(
            f'{sys.executable} -m pip install '
            f'--target="{deps_target}" '
            + " ".join(f'"{d}"' for d in _RUNTIME_DEPS)
        )

        # Build the wheel for typer itself (--no-deps: deps handled above).
        self.run(
            f'{sys.executable} -m pip install --no-deps '
            f'--target="{install_target}" "{self.source_folder}"'
        )

    def package(self):
        install_target = os.path.join(self.build_folder, "install")
        deps_target = os.path.join(self.build_folder, "deps")

        # typer wheel contents.
        copy(self, "*", dst=self.package_folder, src=install_target)
        # Runtime dependencies installed via pip.
        copy(self, "*", dst=self.package_folder, src=deps_target)

    def package_info(self):
        # Pure-Python: no compiled artifacts.
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

        # Expose the flat pip --target layout on PYTHONPATH so that
        # `import typer` (and its runtime deps) resolve at consume time.
        self.runenv_info.prepend_path("PYTHONPATH", self.package_folder)
        self.buildenv_info.prepend_path("PYTHONPATH", self.package_folder)
