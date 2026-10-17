#!/usr/bin/env python3
"""Conan recipe for notebook-shim 0.2.3."""

import json
import os
import py_compile
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class NotebookShimConan(ConanFile):
    name = "notebook-shim"
    version = "0.2.3"
    description = "Shim layer for Notebook traits and configuration used by Jupyter Server"
    license = "BSD-3-Clause"
    homepage = "https://github.com/jupyter/notebook_shim"
    url = "https://github.com/jupyter/notebook_shim"
    package_type = "unknown"
    settings = "os", "compiler", "build_type", "arch"

    _module_files = [
        "__init__.py",
        "_version.py",
        "nbserver.py",
        "shim.py",
        "traits.py",
    ]

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        self._validate_pyproject()
        self._validate_extension_config()
        self._compile_python_sources()

    def package(self):
        module_src = os.path.join(self.source_folder, "notebook_shim")
        module_dst = os.path.join(self.package_folder, "lib", "python", "notebook_shim")
        copy(self, "*.py", src=module_src, dst=module_dst)
        copy(
            self,
            "notebook_shim.json",
            src=os.path.join(self.source_folder, "jupyter_server_config.d"),
            dst=os.path.join(self.package_folder, "etc", "jupyter", "jupyter_server_config.d"),
        )
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "notebook-shim"),
             keep_path=False)

    def package_info(self):
        python_dir = os.path.join(self.package_folder, "lib", "python")
        config_dir = os.path.join(self.package_folder, "etc", "jupyter")
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path("PYTHONPATH", python_dir)
        self.runenv_info.prepend_path("JUPYTER_CONFIG_PATH", config_dir)

    def package_id(self):
        self.info.clear()

    def _validate_pyproject(self):
        pyproject = os.path.join(self.source_folder, "pyproject.toml")
        text = self._read(pyproject)
        if 'name = "notebook_shim"' not in text:
            raise ConanInvalidConfiguration("pyproject.toml does not declare notebook_shim")
        version_file = os.path.join(self.source_folder, "notebook_shim", "_version.py")
        version_text = self._read(version_file)
        match = re.search(r'__version__\s*=\s*"([^"]+)"', version_text)
        if not match or match.group(1) != self.version:
            raise ConanInvalidConfiguration("notebook_shim/_version.py version mismatch")

    def _validate_extension_config(self):
        config = os.path.join(self.source_folder, "jupyter_server_config.d", "notebook_shim.json")
        data = json.loads(self._read(config))
        enabled = data.get("ServerApp", {}).get("jpserver_extensions", {}).get("notebook_shim")
        if enabled is not True:
            raise ConanInvalidConfiguration("notebook_shim Jupyter Server extension is not enabled")

    def _compile_python_sources(self):
        module_src = os.path.join(self.source_folder, "notebook_shim")
        for filename in self._module_files:
            path = os.path.join(module_src, filename)
            if not os.path.isfile(path):
                raise ConanInvalidConfiguration(f"Missing notebook_shim module file: {filename}")
            py_compile.compile(path, doraise=True)

    def _read(self, path):
        with open(path, encoding="utf-8") as stream:
            return stream.read()
