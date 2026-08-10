#!/usr/bin/env python3
"""
aioredis/1.3.1 — Conan recipe
==============================
Pure Python asyncio Redis client (PEP 3156). No C/C++ compilation needed.
The package simply copies the aioredis/ Python source directory into the
package folder. Runtime Python dependencies (async-timeout, hiredis optional,
typing-extensions) are documented in notes.md — they are not Conan dependencies.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, export_conandata_patches
from conan.tools.layout import basic_layout


class AioredisRecipe(ConanFile):
    name = "aioredis"
    version = "1.3.1"
    description = "asyncio (PEP 3156) Redis client — Python library for async Redis access"
    license = "MIT"
    homepage = "https://github.com/aio-libs-abandoned/aioredis-py"
    url = "https://github.com/aio-libs-abandoned/aioredis-py"
    topics = ("redis", "asyncio", "async", "python", "client")
    package_type = "header-library"
    settings = "os", "arch"
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Python runtime dependencies (async-timeout, hiredis optional,
        # typing-extensions) are NOT Conan dependencies — documented in notes.md.
        pass

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def build(self):
        # Pure Python library — no compilation needed.
        pass

    def package(self):
        # Copy the aioredis Python package directory (all .py files recursively).
        copy(self, "*.py", os.path.join(self.source_folder, "aioredis"),
             os.path.join(self.package_folder, "lib", "aioredis"), keep_path=True)
        # Copy LICENSE.
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "COPYING*", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = ["lib"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
