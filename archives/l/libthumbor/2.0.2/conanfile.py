#!/usr/bin/env python3
"""Conan recipe for libthumbor's pure-Python URL helpers."""

import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class LibthumborConan(ConanFile):
    name = "libthumbor"
    version = "2.0.2"
    description = "Python helpers for generating and signing Thumbor URLs"
    license = "MIT"
    homepage = "https://github.com/thumbor/libthumbor"
    url = "https://github.com/thumbor/libthumbor"
    package_type = "unknown"

    settings = "os", "compiler", "build_type", "arch"
    requires = "six/1.17.0"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libthumbor 2.0.2 supports Linux and OHOS only, got {self.settings.os}"
            )

    def package_id(self):
        # The package contains Python source only and is architecture independent.
        self.info.clear()

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )

    def export_sources(self):
        # Source is pinned and fetched in source(); keep this hook for recipe policy.
        pass

    def build(self):
        apply_conandata_patches(self)
        # Keep test tools outside the package and avoid venv's ensurepip
        # bootstrap: the CI worker's Python can create the environment but its
        # ensurepip step exits non-zero. Conan's interpreter has pip available.
        python = sys.executable
        test_deps = os.path.join(self.build_folder, "test-deps")
        self.run(
            f'"{python}" -m pip install --disable-pip-version-check '
            f'--target "{test_deps}" '
            '"pytest==8.4.2" "preggy==1.4.4" "Django==5.2.6"',
            env="conanbuild",
        )

        compatibility_plugin = os.path.join(self.build_folder, "pytest_compat.py")
        with open(compatibility_plugin, "w", encoding="utf-8") as plugin:
            plugin.write(
                "import pytest\n"
                "def _skip_if(condition, reason):\n"
                "    return pytest.mark.skipif(condition, reason=reason)\n"
                "pytest.mark.skip_if = _skip_if\n"
            )
        six_site = os.path.join(
            self.dependencies["six"].package_folder, "lib", "python", "site-packages"
        )
        source_path = os.pathsep.join(
            (test_deps, self.source_folder, six_site, self.build_folder)
        )
        tests = os.path.join(self.source_folder, "tests")
        self.run(
            f'PYTHONPATH="{source_path}" '
            f'"{python}" -m pytest -q -p pytest_compat "{tests}"',
            env="conanbuild",
        )

    def package(self):
        source = os.path.join(self.source_folder, "libthumbor")
        site_packages = os.path.join(
            self.package_folder, "lib", "python", "site-packages"
        )
        copy(self, "*.py", src=source, dst=os.path.join(site_packages, "libthumbor"))
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        site_packages = os.path.join(
            self.package_folder, "lib", "python", "site-packages"
        )
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)
        self.runenv_info.define_path("LIBTHUMBOR_PACKAGE_ROOT", site_packages)
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
