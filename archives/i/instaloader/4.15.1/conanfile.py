#!/usr/bin/env python3
"""Conan recipe for instaloader 4.15.1, built with setuptools as pure Python."""

import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class InstaloaderConan(ConanFile):
    name = "instaloader"
    version = "4.15.1"
    description = "Download Instagram pictures, videos, captions, and metadata"
    license = "MIT"
    homepage = "https://instaloader.github.io/"
    url = "https://github.com/instaloader/instaloader"
    topics = ("instagram", "downloader", "metadata", "python")
    package_type = "application"
    # CI L0 requires the complete OHOS profile settings even for pure Python.
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # Instaloader is pure Python.  Do not invoke the setuptools build
        # backend: clean CI workers may provide pip without setuptools.
        package_src = os.path.join(self.source_folder, "instaloader")
        if not os.path.isdir(package_src):
            raise ConanException(f"instaloader source package is missing: {package_src}")

        old_pythonpath = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = self.source_folder + (
            os.pathsep + old_pythonpath if old_pythonpath else ""
        )
        try:
            ret = self.run(
                "python3 -c \"import instaloader; "
                "assert instaloader.__version__ == '4.15.1'; "
                "assert callable(instaloader.Instaloader); "
                "print('source import/API self-check: OK')\"",
                cwd=self.source_folder,
            )
            if ret != 0:
                raise ConanException(f"source import self-check failed with exit code {ret}")
        finally:
            if old_pythonpath is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = old_pythonpath

    def package(self):
        python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = os.path.join(
            self.package_folder, "lib", python_version, "site-packages"
        )
        os.makedirs(site_packages, exist_ok=True)

        # Copy the pure-Python module directly; this avoids setuptools backend
        # requirements while preserving the complete runtime package.
        shutil.copytree(
            os.path.join(self.source_folder, "instaloader"),
            os.path.join(site_packages, "instaloader"),
        )
        # Install the pure-Python runtime dependency without building sdists.
        ret = self.run(
            f"python3 -m pip install --only-binary=:all: --target \"{site_packages}\" "
            "'requests>=2.25'",
            cwd=self.source_folder,
        )
        if ret != 0:
            raise ConanException(f"requests dependency install failed with exit code {ret}")

        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        launcher = os.path.join(bin_dir, "instaloader")
        with open(launcher, "w", encoding="utf-8") as handle:
            handle.write("#!/bin/sh\n")
            handle.write("HERE=$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\n")
            handle.write(
                f"PYTHONPATH=\"$HERE/../lib/{python_version}/site-packages"
                "${PYTHONPATH:+:$PYTHONPATH}\" \\\n"
            )
            handle.write("export PYTHONPATH\nexec python3 -m instaloader \"$@\"\n")
        os.chmod(launcher, 0o755)

        copy(
            self,
            "LICENSE*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        site_packages = os.path.join(self.package_folder, "lib", python_version, "site-packages")
        self.buildenv_info.append_path("PYTHONPATH", site_packages)
        self.runenv_info.append_path("PYTHONPATH", site_packages)
