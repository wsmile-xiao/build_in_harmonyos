#!/usr/bin/env python3
"""Conan recipe for aiohttp 3.14.3 — async HTTP client/server framework
(pure-Python fallback build, PyPI source).

Builds with AIOHTTP_NO_EXTENSIONS=1 (pure-Python fallback — the Cython
extensions _http_parser/_http_writer are skipped, same mode as yarl).
8 runtime dependencies all published on ohpcd.
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class AiohttpConan(ConanFile):
    name = "aiohttp"
    version = "3.14.3"
    description = "Async http client/server framework (asyncio)"
    license = "Apache-2.0"
    homepage = "https://github.com/aio-libs/aiohttp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "python-require"

    def requirements(self):
        # runtime deps (PyPI requires_dist verified, all on ohpcd)
        self.requires("yarl/1.24.5")
        self.requires("multidict/6.7.1")
        self.requires("idna/3.18")
        self.requires("propcache/0.5.2")
        self.requires("aiosignal/1.4.0")
        self.requires("frozenlist/1.8.0")
        self.requires("attrs/26.1.0")
        self.requires("aiohappyeyeballs/2.7.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        py = sys.executable
        staging = os.path.join(self.build_folder, "pip-stage")
        # pure-Python fallback — skip Cython extensions (yarl mode)
        # env var as command prefix (self.run env arg must be a list)
        self.run(
            f'AIOHTTP_NO_EXTENSIONS=1 {py} -m pip install --no-deps '
            f'--target "{staging}" .',
            cwd=self.source_folder)

    def package(self):
        staging = os.path.join(self.build_folder, "pip-stage")
        if not os.path.isdir(staging):
            raise ConanException(f"pip staging missing: {staging}")
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        os.makedirs(site, exist_ok=True)
        for entry in os.listdir(staging):
            src = os.path.join(staging, entry)
            dst = os.path.join(site, entry)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        if not os.path.isdir(os.path.join(site, "aiohttp")):
            raise ConanException(f"aiohttp package missing under {site}")

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        self.output.info(f"PYTHONPATH={site}")
