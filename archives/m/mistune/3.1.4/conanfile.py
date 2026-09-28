#!/usr/bin/env python3
"""Conan recipe for the pure-Python mistune Markdown parser."""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MistuneConan(ConanFile):
    name = "mistune"
    version = "3.1.4"
    description = "A fast, pure-Python Markdown parser with plugins and renderers"
    license = "BSD-3-Clause"
    homepage = "https://github.com/lepture/mistune"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "python-require"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "test_package/*"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # typing-extensions is declared only for Python < 3.11. The OHOS PC
        # Conan Python is 3.14, so mistune has no runtime package dependency.
        pass

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        source_package = os.path.join(self.source_folder, "src", "mistune")
        upstream_tests = os.path.join(self.source_folder, "tests")
        if not os.path.isdir(source_package):
            raise ConanException("mistune source package directory is missing")
        if not os.path.isdir(upstream_tests):
            raise ConanException("official mistune upstream tests are missing")

        staging = os.path.join(self.build_folder, "python-stage")
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            source_package,
            os.path.join(staging, "mistune"),
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )

        env = dict(os.environ)
        paths = [staging, self.source_folder]
        if env.get("PYTHONPATH"):
            paths.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(paths)
        command = [
            sys.executable,
            "-X",
            "utf8",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-t",
            ".",
            "-q",
        ]
        result = subprocess.run(
            command,
            cwd=self.source_folder,
            env=env,
            capture_output=True,
            text=True,
        )
        print("[mistune 3.1.4 official upstream unittest suite]")
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip())
        if result.returncode != 0:
            raise ConanException(
                "mistune official upstream tests failed with exit code "
                + str(result.returncode)
            )

    def package(self):
        staging = os.path.join(self.build_folder, "python-stage", "mistune")
        if not os.path.isdir(staging):
            raise ConanException("staged mistune Python package is missing")

        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        os.makedirs(site, exist_ok=True)
        shutil.copytree(staging, os.path.join(site, "mistune"))
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PYTHONPATH", site)
