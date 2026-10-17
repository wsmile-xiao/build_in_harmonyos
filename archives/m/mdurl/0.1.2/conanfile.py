#!/usr/bin/env python3
"""Conan recipe for packaging the pure-Python mdurl 0.1.2 library."""

import os
import sys

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class MdurlConan(ConanFile):
    name = "mdurl"
    version = "0.1.2"
    description = "Markdown URL utilities"
    license = "MIT"
    homepage = "https://github.com/executablebooks/mdurl"
    url = "https://github.com/executablebooks/mdurl"

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

    def build(self):
        apply_conandata_patches(self)

        test_deps = os.path.join(self.build_folder, "_test_deps")
        self.run(
            f'"{sys.executable}" -m pip install '
            "--disable-pip-version-check --no-compile "
            f'--target "{test_deps}" "pytest==9.1.1"'
        )

        test_env = Environment()
        test_env.prepend_path("PYTHONPATH", os.path.join(self.source_folder, "src"))
        test_env.prepend_path("PYTHONPATH", test_deps)
        with test_env.vars(self).apply():
            self.run(
                f'"{sys.executable}" -m pytest -q '
                f'"{os.path.join(self.source_folder, "tests")}"',
                cwd=self.source_folder,
            )

    def package(self):
        module_src = os.path.join(self.source_folder, "src", "mdurl")
        module_dst = os.path.join(
            self.package_folder,
            "lib",
            "python",
            "site-packages",
            "mdurl",
        )
        copy(self, "*.py", src=module_src, dst=module_dst, keep_path=False)
        copy(self, "py.typed", src=module_src, dst=module_dst, keep_path=False)
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
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
