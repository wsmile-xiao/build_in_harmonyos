#!/usr/bin/env python3
"""Conan recipe — autotiling 1.9.3 (pure Python CLI tool, setuptools).

HarmonyOS PC adaptation: pure-Python noarch tool for sway/i3 that switches
the horizontal/vertical split orientation based on the focused window
dimensions. Installed via pip --prefix into a staging area; the
console_scripts entry `autotiling` lands in bin/. Runtime dep i3ipc is not
published as a conan recipe, so pip resolves it from the pypi.cnb.cool
mirror during install into the same site-packages (same approach as
airthings-ble). No C/C++ compilation.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class AutotilingConan(ConanFile):
    name = "autotiling"
    version = "1.9.3"
    description = ("Automatically switch the horizontal/vertical window "
                   "split orientation in sway and i3")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/nwg-piotr/autotiling"
    url = "https://github.com/nwg-piotr/autotiling"

    package_type = "application"

    # Pure Python noarch: no compiler needed (same pattern as acronym),
    # but L0p gate requires the full OHOS profile set (os/compiler/build_type/arch).
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _site_packages(self, base):
        ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        return os.path.join(base, "lib", ver, "site-packages")

    def build(self):
        apply_conandata_patches(self)
        python_exe = sys.executable
        src_dir = self.source_folder
        stage = os.path.join(self.build_folder, "stage")
        os.makedirs(stage, exist_ok=True)

        # pip install . --prefix: builds from source (setuptools), places
        # console_scripts in stage/bin. Runtime dep i3ipc is NOT published
        # as a conan recipe, so pip resolves it from the pypi.cnb.cool
        # mirror into the same site-packages (airthings-ble pattern).
        self.run(
            f"{python_exe} -m pip install . --prefix=\"{stage}\"",
            cwd=src_dir,
        )
        site = self._site_packages(stage)
        if not os.path.isdir(os.path.join(site, "autotiling")):
            raise ConanException(f"autotiling package missing under {site}")

    def package(self):
        stage = os.path.join(self.build_folder, "stage")
        if not os.path.isdir(stage):
            raise ConanException(f"stage directory not found: {stage}, nothing to package")
        for item in os.listdir(stage):
            src = os.path.join(stage, item)
            dst = os.path.join(self.package_folder, item)
            if os.path.isdir(src):
                copy(self, "*", src=src, dst=dst)
            else:
                copy(self, item, src=stage, dst=self.package_folder)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        site = self._site_packages(self.package_folder)
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
            self.buildenv_info.append_path("PATH", bin_path)
