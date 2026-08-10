#!/usr/bin/env python3
"""Conan recipe for the pure-Python acstore package."""

import os
import sys

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, download, export_conandata_patches, get, unzip


class AcstoreConan(ConanFile):
    name = "acstore"
    version = "0.20260411"
    description = "Attribute Container Storage implementation."
    license = "Apache-2.0"
    homepage = "https://github.com/log2timeline/acstore"
    url = "https://github.com/log2timeline/acstore"
    settings = "os", "arch"
    package_type = "library"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # PyYAML is a Python runtime dependency and is installed into the
        # isolated package tree during build; it is not a Conan recipe here.
        pass

    def layout(self):
        self.folders.source = "src"
        self.folders.build = "build"

    def source(self):
        source = self.conan_data["sources"][0]
        try:
            get(self, **source, strip_root=True)
            return
        except Exception as direct_error:
            self.output.warning(
                f"Official source download failed ({direct_error}); trying mirror fallback."
            )

        mirror_url = (
            "https://ghproxy.net/https%3A%2F%2Fgithub.com%2Flog2timeline%2Facstore%2F"
            "archive%2Frefs%2Ftags%2F20260411.tar.gz"
        )
        archive = os.path.join(self.downloads_folder, "acstore-20260411.tar.gz")
        download(self, mirror_url, archive, sha256=source["sha256"])
        unzip(self, archive, self.source_folder, strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        staging = os.path.join(self.build_folder, "staging")
        os.makedirs(staging, exist_ok=True)
        pip = sys.executable
        # Install the patched source tree. apply_conandata_patches patches
        # the source copy, so install from self.source_folder.
        # --break-system-packages is needed on PEP 668 hosts
        # (Debian/Ubuntu-derived); --no-compile keeps the staged tree
        # reproducible; --target isolates the install.
        self.run(
            f'"{pip}" -m pip install --break-system-packages '
            f'--no-compile --target="{staging}" "{self.source_folder}"'
        )

    def package(self):
        import shutil
        staging = os.path.join(self.build_folder, "staging")
        pyver = f"{sys.version_info.major}.{sys.version_info.minor}"
        dst = os.path.join(self.package_folder, f"lib/python{pyver}/site-packages")
        os.makedirs(dst, exist_ok=True)
        # shutil.copytree copies the whole staged tree including the
        # acstore.helpers and acstore.containers subpackages; Conan's
        # copy() with "*" does not recurse into subdirectories.
        for entry in os.listdir(staging):
            src_path = os.path.join(staging, entry)
            dst_path = os.path.join(dst, entry)
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            else:
                shutil.copy2(src_path, dst_path)

    def package_info(self):
        pyver = f"{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = f"lib/python{pyver}/site-packages"
        self.runenv_info.append_path("PYTHONPATH", os.path.join(self.package_folder, site_packages))
        self.buildenv_info.append_path("PYTHONPATH", os.path.join(self.package_folder, site_packages))
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
