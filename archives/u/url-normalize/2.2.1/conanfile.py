#!/usr/bin/env python3
"""Conan recipe for the pure-Python url-normalize 2.2.1 library."""

import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)


class UrlNormalizeConan(ConanFile):
    name = "url-normalize"
    version = "2.2.1"
    description = "URL normalization for Python"
    license = "MIT AND BSD-3-Clause"
    homepage = "https://github.com/niksite/url-normalize"
    url = "https://github.com/niksite/url-normalize"

    package_type = "unknown"
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        self.settings.rm_safe("os.version")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

        idna_source = self._idna_source()
        os.makedirs(idna_source, exist_ok=True)
        get(
            self,
            **self.conan_data["idna"],
            destination=idna_source,
            strip_root=True,
        )

    def _idna_source(self):
        return os.path.join(self.source_folder, "_conan_idna")

    def _install_root(self):
        return os.path.join(self.build_folder, "_upstream_install")

    def _pip_install_source(self, source, target):
        self.run(
            f'"{sys.executable}" -m pip install '
            "--disable-pip-version-check --no-compile --no-deps "
            f'--no-build-isolation --target "{target}" "{source}"'
        )

    def build(self):
        apply_conandata_patches(self)

        install_root = self._install_root()
        build_deps = os.path.join(self.build_folder, "_build_deps")
        test_deps = os.path.join(self.build_folder, "_test_deps")
        pytest_tmp = os.path.join(self.build_folder, "_pytest_tmp")
        for path in (install_root, build_deps, test_deps, pytest_tmp):
            rmdir(self, path)
            os.makedirs(path, exist_ok=True)

        # Keep PEP 517 backends explicit and isolated. idna uses flit_core,
        # while url-normalize uses setuptools. These are build-only tools.
        self.run(
            f'"{sys.executable}" -m pip install '
            "--disable-pip-version-check --no-compile "
            f'--target "{build_deps}" '
            '"flit_core==3.12.0" "setuptools==75.3.2" "wheel==0.45.1"'
        )

        # url-normalize imports the third-party idna package at runtime.
        # Pin and install the official idna 3.15 sdist so the Conan package is
        # self-contained and keeps url-normalize's Python >=3.8 compatibility.
        build_env = Environment()
        build_env.prepend_path("PYTHONPATH", build_deps)
        with build_env.vars(self).apply():
            self._pip_install_source(self._idna_source(), install_root)
            self._pip_install_source(self.source_folder, install_root)

        # Upstream's pyproject config enables coverage and socket isolation.
        # Install the exact test runners into the isolated Conan build folder.
        self.run(
            f'"{sys.executable}" -m pip install '
            "--disable-pip-version-check --no-compile "
            f'--target "{test_deps}" '
            '"pytest==9.1.1" "pytest-cov==6.2.1" "coverage==7.8.0" '
            '"pytest-socket==0.8.0"'
        )

        test_env = Environment()
        test_env.prepend_path("PYTHONPATH", install_root)
        test_env.prepend_path("PYTHONPATH", test_deps)
        test_env.define("PYTHONDONTWRITEBYTECODE", "1")
        test_env.define("TMPDIR", pytest_tmp)
        with test_env.vars(self).apply():
            self.run(
                f'"{sys.executable}" -m pytest -q -s '
                f'--rootdir "{self.source_folder}" '
                f'-c "{os.path.join(self.source_folder, "pyproject.toml")}" '
                f'"{os.path.join(self.source_folder, "tests")}"',
                cwd=self.build_folder,
            )

    def package(self):
        install_root = self._install_root()
        site_packages = os.path.join(
            self.package_folder,
            "lib",
            "python",
            "site-packages",
        )

        packaged_directories = (
            "url_normalize",
            "url_normalize-2.2.1.dist-info",
            "idna",
            "idna-3.15.dist-info",
        )
        for directory in packaged_directories:
            source = os.path.join(install_root, directory)
            if not os.path.isdir(source):
                raise ConanInvalidConfiguration(
                    f"Expected installed Python package directory is missing: {source}"
                )
            copy(
                self,
                "*",
                src=source,
                dst=os.path.join(site_packages, directory),
            )

        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE.md",
            src=self._idna_source(),
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        site_packages = os.path.join(
            self.package_folder,
            "lib",
            "python",
            "site-packages",
        )
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
