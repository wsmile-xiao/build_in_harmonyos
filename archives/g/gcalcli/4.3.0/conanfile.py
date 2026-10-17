#!/usr/bin/env python3
"""Conan recipe for gcalcli 4.3.0 — Google Calendar CLI (Python setuptools)."""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class GcalcliConan(ConanFile):
    name = "gcalcli"
    version = "4.3.0"
    description = "Google Calendar Command Line Interface"
    license = "MIT"
    homepage = "https://github.com/insanum/gcalcli"
    url = "https://github.com/insanum/gcalcli"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        ret = self.run("python3 -m pip install setuptools --quiet 2>&1", cwd=self.source_folder)
        if ret != 0:
            raise ConanException(f"pip install setuptools failed with exit code {ret}")
        ret = self.run("python3 setup.py build", cwd=self.source_folder)
        if ret != 0:
            raise ConanException(f"setup.py build failed with exit code {ret}")
        # Install runtime deps (--no-deps: system already has transitive deps like cryptography)
        ret = self.run(
            "python3 -m pip install --no-deps "
            "'google-api-python-client>=1.4' httplib2 oauth2client "
            "parsedatetime python-dateutil vobject --quiet 2>&1",
            cwd=self.source_folder,
        )
        if ret != 0:
            raise ConanException(f"pip install runtime deps failed with exit code {ret}")

    def package(self):
        ret = self.run(
            f"python3 setup.py install --prefix={self.package_folder}",
            cwd=self.source_folder,
        )
        if ret != 0:
            raise ConanException(f"setup.py install failed with exit code {ret}")
        # Install runtime deps into package so gcalcli works standalone
        deps_target = os.path.join(self.package_folder, "gcalcli-deps")
        ret = self.run(
            f"python3 -m pip install --no-deps "
            "'google-api-python-client>=1.4' httplib2 oauth2client "
            "parsedatetime python-dateutil vobject "
            f"--target={deps_target} --quiet 2>&1",
            cwd=self.source_folder,
        )
        if ret != 0:
            raise ConanException(f"pip install deps to target failed with exit code {ret}")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        # Add gcalcli-deps to PYTHONPATH so gcalcli can find runtime deps
        self.runenv_info.append_path("PYTHONPATH", os.path.join(self.package_folder, "gcalcli-deps"))
        # setup.py install --prefix= puts metadata under lib/python3.*/site-packages/
        pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        self.runenv_info.append_path("PYTHONPATH", os.path.join(self.package_folder, "lib", pyver, "site-packages"))
