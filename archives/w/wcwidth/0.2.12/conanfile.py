#!/usr/bin/env python3
"""Conan recipe for wcwidth 0.2.12, a pure-Python setuptools package."""

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
import os
import shutil
import sys


class WcwidthConan(ConanFile):
    name = "wcwidth"
    version = "0.2.12"
    description = "Measures the displayed width of unicode strings in a terminal"
    license = "MIT"
    homepage = "https://github.com/jquast/wcwidth"
    url = "https://github.com/jquast/wcwidth"
    topics = ("python", "unicode", "terminal", "wcwidth")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("wcwidth supports Linux and OHOS hosts")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        python = self._python()
        test_deps = os.path.join(self.build_folder, "test-deps")
        self.run(
            f'"{python}" -m pip install --target "{test_deps}" pytest',
            cwd=self.source_folder,
        )
        old_pythonpath = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = test_deps + (
            os.pathsep + old_pythonpath if old_pythonpath else ""
        )
        try:
            self.run(
                f'"{python}" -m pytest -o addopts="" -q',
                cwd=self.source_folder,
            )
        finally:
            if old_pythonpath is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = old_pythonpath

    def package(self):
        site_packages = os.path.join(
            self.package_folder, "lib",
            f"python{sys.version_info.major}.{sys.version_info.minor}",
            "site-packages",
        )
        os.makedirs(site_packages, exist_ok=True)
        copy(self, "*.py", src=os.path.join(self.source_folder, "wcwidth"), dst=os.path.join(site_packages, "wcwidth"))
        copy(self, "*.txt", src=os.path.join(self.source_folder, "wcwidth"), dst=os.path.join(site_packages, "wcwidth"))
        copy(self, "*.md", src=os.path.join(self.source_folder, "wcwidth"), dst=os.path.join(site_packages, "wcwidth"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
        site_packages = os.path.join(
            self.package_folder, "lib",
            f"python{sys.version_info.major}.{sys.version_info.minor}",
            "site-packages",
        )
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)

    @staticmethod
    def _python():
        candidates = [
            os.environ.get("HMBS_PYTHON3"),
            shutil.which("python3"),
            sys.executable,
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration("python3 interpreter not found")
