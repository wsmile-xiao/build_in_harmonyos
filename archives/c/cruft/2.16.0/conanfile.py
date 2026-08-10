#!/usr/bin/env python3
"""Conan recipe for cruft 2.16.0 - pure Python package (hatchling build backend).

cruft is a CLI tool for maintaining Cookiecutter-based project templates.
No C/C++ compilation required - pure Python wheel (py3-none-any).
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class CruftConan(ConanFile):
    name = "cruft"
    version = "2.16.0"
    license = "MIT"
    author = "Timothy Crosley <timothy.crosley@gmail.com>, Sambhav Kothari <sambhavs.email@gmail.com>"
    url = "https://github.com/cruft/cruft"
    homepage = "https://cruft.github.io/cruft/"
    description = (
        "Allows you to maintain all the necessary cruft for packaging and "
        "building projects separate from the code you intentionally write. "
        "Built on-top of, and fully compatible with, CookieCutter."
    )
    topics = ("python", "cookiecutter", "template", "project-management")
    package_type = "application"
    settings = "os", "arch"
    exports_sources = "sitecustomize.py"

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        python_exe = sys.executable

        # Step 1: Install runtime dependencies to system Python.
        # Versions are pinned to match upstream uv.lock and avoid
        # newer Typer/Click prompt behavior that can block on OHOS.
        self.run(
            f'"{python_exe}" -m pip install --break-system-packages '
            '"cookiecutter==2.6.0" "gitpython==3.1.43" '
            '"typer==0.15.1" "click==8.1.8" "toml==0.10.2"',
            env="conanrun",
        )

        # Step 2: Install cruft itself to a staging directory (no deps).
        staging = os.path.join(self.build_folder, "staging")
        self.run(
            f'"{python_exe}" -m pip install --no-deps --break-system-packages '
            f'--prefix="{staging}" "{self.source_folder}"',
            env="conanrun",
        )

    def package(self):
        # Copy installed files from staging to package folder
        staging = os.path.join(self.build_folder, "staging")
        copy(self, "*", dst=self.package_folder, src=staging)

        # Copy sitecustomize.py into site-packages for OHOS subprocess fix
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        copy(
            self,
            "sitecustomize.py",
            dst=site_packages,
            src=self.export_sources_folder,
        )

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = os.path.join("lib", py_ver, "site-packages")

        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = [site_packages]
        self.cpp_info.includedirs = []

        bin_path = os.path.join(self.package_folder, "bin")
        lib_path = os.path.join(self.package_folder, site_packages)

        self.output.info(f"Appending PATH environment variable: {bin_path}")
        self.runenv_info.prepend_path("PATH", bin_path)

        self.output.info(f"Setting PYTHONPATH: {lib_path}")
        self.runenv_info.prepend_path("PYTHONPATH", lib_path)
