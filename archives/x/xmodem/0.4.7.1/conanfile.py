#!/usr/bin/env python3
"""Conan recipe for packaging the pure-Python xmodem 0.4.7 library."""

import os
import shutil
import sys

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import copy, get


class XmodemConan(ConanFile):
    name = "xmodem"
    version = "0.4.7.1"
    description = "XMODEM protocol implementation"
    license = "MIT"
    homepage = "https://github.com/tehmaze/xmodem"
    url = "https://github.com/tehmaze/xmodem"

    package_type = "unknown"
    settings = "os", "arch"
    _source_url = "https://github.com/tehmaze/xmodem/archive/refs/tags/0.4.7.tar.gz"
    _source_sha256 = "ed5d0563d6b5bfbeeaceb7a17e07738b7ce60af0e7323ca3e2a6e49942855519"

    def configure(self):
        self.settings.rm_safe("os.version")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(
            self,
            url=self._source_url,
            sha256=self._source_sha256,
            strip_root=True,
        )

    def build(self):
        test_deps = os.path.join(self.build_folder, "_test_deps")
        self.run(
            f'"{sys.executable}" -m pip install '
            "--disable-pip-version-check --no-compile "
            f'--target "{test_deps}" "pytest==8.4.2"'
        )

        test_env = Environment()
        test_env.prepend_path("PYTHONPATH", self.source_folder)
        test_env.prepend_path("PYTHONPATH", test_deps)

        rb = shutil.which("rb") or shutil.which("lrb")
        sb = shutil.which("sb") or shutil.which("lsb")
        test_path = (
            os.path.join(self.source_folder, "test")
            if rb and sb
            else os.path.join(self.source_folder, "test", "unit")
        )

        with test_env.vars(self).apply():
            self.run(
                f'"{sys.executable}" -m pytest -q "{test_path}"',
                cwd=self.source_folder,
            )

    def package(self):
        module_src = os.path.join(self.source_folder, "xmodem")
        module_dst = os.path.join(
            self.package_folder,
            "lib",
            "python",
            "site-packages",
            "xmodem",
        )
        copy(self, "*.py", src=module_src, dst=module_dst, keep_path=True)
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "*.TXT",
            src=os.path.join(self.source_folder, "doc"),
            dst=os.path.join(self.package_folder, "share", "xmodem", "doc"),
            keep_path=False,
        )
        copy(
            self,
            "*.txt",
            src=os.path.join(self.source_folder, "doc"),
            dst=os.path.join(self.package_folder, "share", "xmodem", "doc"),
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
