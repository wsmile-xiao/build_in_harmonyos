#!/usr/bin/env python3
"""Conan recipe for typobuster 1.0.0 — Python GTK3 text editor.

Pure Python application built with setuptools (setup.py). Build installs into
a staging directory, then packages the installed tree by locating
site-packages / bin / share. ``setup.py check`` is invoked before install to
validate the upstream package metadata.
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class TypobusterConan(ConanFile):
    name = "typobuster"
    version = "1.0.0"
    description = "Lightweight GTK text editor with transformations and typo correction"
    license = "GPL-3.0-only"
    homepage = "https://github.com/nwg-piotr/typobuster"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.source = "src"
        self.folders.build = "build"

    def source(self):
        # The codeload URL has no filename suffix; make Conan select tar.gz
        # extraction instead of treating the downloaded archive as a ZIP.
        get(self, **self.conan_data["sources"], filename="v1.0.0.tar.gz", strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        src_dir = self.source_folder

        # Ensure setuptools is available (OHOS system Python may lack it).
        # --break-system-packages bypasses PEP 668 externally-managed guard.
        self.run(
            f'{sys.executable} -m pip install --break-system-packages '
            f'--timeout 120 --retries 3 setuptools',
            env="conanrun",
        )

        # Validate upstream package metadata before install.
        self.run(f'"{sys.executable}" setup.py check', cwd=src_dir)

        staging = os.path.join(self.build_folder, "staging")
        os.makedirs(staging, exist_ok=True)
        self.run(
            f'"{sys.executable}" setup.py install --root="{staging}" --no-compile',
            cwd=self.source_folder,
        )

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        pyver = f"{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = os.path.join(self.package_folder, "lib", f"python{pyver}", "site-packages")

        for root, dirs, files in os.walk(staging):
            if os.path.basename(root) == "site-packages" and "typobuster" in dirs:
                copy(self, "*", root, site_packages)
            elif os.path.basename(root) == "bin" and "typobuster" in files:
                copy(self, "typobuster", root, os.path.join(self.package_folder, "bin"))

        copy(self, "typobuster.desktop", self.source_folder, os.path.join(self.package_folder, "share", "applications"))
        copy(self, "typobuster.svg", self.source_folder, os.path.join(self.package_folder, "share", "pixmaps"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "share", "doc", "typobuster"))

    def package_info(self):
        pyver = f"{sys.version_info.major}.{sys.version_info.minor}"
        self.runenv_info.append_path(
            "PYTHONPATH", os.path.join(self.package_folder, "lib", f"python{pyver}", "site-packages")
        )
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
