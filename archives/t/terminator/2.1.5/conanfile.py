#!/usr/bin/env python3
"""Conan recipe for terminator 2.1.5 — Python GTK/VTE terminal emulator.

This is a pure Python application built with setuptools (setup.py).
Build uses ``setup.py install`` into a staging directory, then packages
the installed tree by locating site-packages / bin / share.
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class TerminatorConan(ConanFile):
    name = "terminator"
    version = "2.1.5"
    description = "GNOME multiple terminal emulator (Python/GTK)"
    license = "GPL-2.0"
    homepage = "https://github.com/gnome-terminator/terminator"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"

    # R32: settings.os judgment must use in ("Linux", "OHOS"), not == "Linux"
    settings = "os", "arch"

    # No binary exports — pure Python
    package_type = "application"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.build = "build"
        self.folders.source = "src"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        install_root = os.path.join(self.build_folder, "staging")
        os.makedirs(install_root, exist_ok=True)

        src_dir = self.source_folder

        # Ensure setuptools is available (OHOS system Python may lack it)
        # --break-system-packages bypasses PEP 668 externally-managed guard
        # --timeout/--retries for resilience against PyPI mirror network issues
        self.run(
            f'{sys.executable} -m pip install --break-system-packages '
            f'--timeout 120 --retries 3 setuptools',
            env="conanrun",
        )

        # Use --without-gettext to avoid intltool-merge dependency (not on OHOS)
        # setup.py install --root prepends install_root to sys.prefix paths
        self.run(
            f'{sys.executable} setup.py --without-gettext install '
            f'--root={install_root} --no-compile',
            cwd=src_dir,
        )

    def package(self):
        staging = os.path.join(self.build_folder, "staging")

        pyver = "{}.{}".format(sys.version_info.major, sys.version_info.minor)
        site_packages_dst = os.path.join(self.package_folder, f"lib/python{pyver}/site-packages")
        bin_dst = os.path.join(self.package_folder, "bin")
        share_dst = os.path.join(self.package_folder, "share")

        # Walk the staging tree to find site-packages, bin, share directories
        for root, dirs, files in os.walk(staging):
            base = os.path.basename(root)
            # Find site-packages with terminatorlib
            if base == "site-packages" and "terminatorlib" in dirs:
                copy(self, "*", root, site_packages_dst)
            # Find bin directory with terminator script
            elif base == "bin" and ("terminator" in files or "remotinator" in files):
                copy(self, "*", root, bin_dst)
            # Find share directory with terminator data
            elif base == "share" and "applications" in dirs:
                copy(self, "*", root, share_dst)

    def package_info(self):
        pyver = "{}.{}".format(sys.version_info.major, sys.version_info.minor)
        python_site = f"lib/python{pyver}/site-packages"
        pythonpath = os.path.join(self.package_folder, python_site)
        self.runenv_info.append_path("PYTHONPATH", pythonpath)
        self.buildenv_info.append_path("PYTHONPATH", pythonpath)

        # Expose the bin directory
        self.cpp_info.bindirs = ["bin"]
        # No shared/static libs for a pure Python package
        self.cpp_info.libdirs = []
