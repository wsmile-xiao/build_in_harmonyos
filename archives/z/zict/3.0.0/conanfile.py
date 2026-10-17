#!/usr/bin/env python3
"""Conan recipe for zict 3.0.0, a dependency-free pure-Python mapping library."""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class ZictConan(ConanFile):
    name = "zict"
    version = "3.0.0"
    description = "Mutable mapping tools for caching and storage"
    license = "BSD-3-Clause"
    homepage = "https://github.com/dask/zict"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Pure Python, but L0 requires the complete OHOS host/build profile tuple.
    settings = "os", "arch", "compiler", "build_type"
    package_type = "python-require"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        python = sys.executable
        test_deps = os.path.join(self.build_folder, "test-deps")
        basetemp = os.path.join(self.build_folder, "pytest-tmp")
        staging = os.path.join(self.build_folder, "pip-stage")

        # Keep build-only pytest dependencies out of the published package.
        # Explicit basetemp avoids pytest's ownership check on the HarmonyOS
        # FUSE-backed default /storage/.../pytest-of-<uid> directory.
        pip = f'env -u PIP_TARGET -u PIP_ONLY_BINARY "{python}" -m pip'
        self.run(
            f'{pip} install --disable-pip-version-check --timeout 120 --retries 3 '
            f'--target "{test_deps}" pytest pytest-asyncio pytest-repeat pytest-timeout'
        )
        test_pythonpath = os.pathsep.join((test_deps, self.source_folder))
        self.run(
            f'PYTHONPATH="{test_pythonpath}" "{python}" -m pytest '
            f'-o addopts= -vv --timeout=180 '
            f'--timeout-method=signal --basetemp="{basetemp}" zict/tests',
            cwd=self.source_folder,
        )

        self.run(
            f'{pip} install --disable-pip-version-check --timeout 120 --retries 3 '
            f'--no-deps --no-compile --target "{staging}" "{self.source_folder}"'
        )

    def package(self):
        staging = os.path.join(self.build_folder, "pip-stage")
        package_root = os.path.join(staging, "zict")
        if not os.path.isdir(package_root):
            raise ConanException(f"zict package missing from pip staging: {staging}")

        py_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = os.path.join(
            self.package_folder, "lib", py_version, "site-packages"
        )
        os.makedirs(site_packages, exist_ok=True)
        for entry in os.listdir(staging):
            source = os.path.join(staging, entry)
            destination = os.path.join(site_packages, entry)
            if os.path.isdir(source):
                shutil.copytree(
                    source,
                    destination,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                )
                direct_url = os.path.join(destination, "direct_url.json")
                if os.path.isfile(direct_url):
                    os.remove(direct_url)
            else:
                shutil.copy2(source, destination)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []

        py_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = os.path.join(
            self.package_folder, "lib", py_version, "site-packages"
        )
        self.runenv_info.append_path("PYTHONPATH", site_packages)
        self.buildenv_info.append_path("PYTHONPATH", site_packages)
