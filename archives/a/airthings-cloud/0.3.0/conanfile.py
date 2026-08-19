#!/usr/bin/env python3
"""Conan recipe for airthings-cloud 0.3.0 — Airthings cloud API client
(pure Python, aiohttp-based, PyPI source).

Dependency: aiohttp >= 3.13.0 — published on ohpcd (aiohttp/3.14.3).
self.run env arg must be a list — use command-prefix env vars.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class AirthingsCloudConan(ConanFile):
    name = "airthings-cloud"
    version = "0.3.0"
    description = "Airthings cloud API client (aiohttp-based)"
    license = "MIT"
    homepage = "https://github.com/Danielhiversen/pyAirthings"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "python-require"

    def requirements(self):
        # aiohttp published on ohpcd (>= 3.13.0 satisfied by 3.14.3)
        self.requires("aiohttp/3.14.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        stage = os.path.join(self.build_folder, "py-stage")
        # pure Python — pip install into staging (no deps: aiohttp is a
        # conan require; --no-deps avoids pulling it via pip).
        # Requires-Python >= 3.13.0 is stricter than the runtime (3.12) —
        # pure-Python code is 3.12-compatible, skip the check.
        self.run(f"python3 -m pip install --no-deps --ignore-requires-python "
                 f"--target='{stage}' .",
                 cwd=self.source_folder)
        if not os.path.isdir(os.path.join(stage, "airthings")):
            raise ConanException(f"airthings package missing under {stage}")

    def package(self):
        stage = os.path.join(self.build_folder, "py-stage")
        for entry in os.listdir(stage):
            s = os.path.join(stage, entry)
            d = os.path.join(self.package_folder, "site-packages", entry)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                os.makedirs(os.path.dirname(d), exist_ok=True)
                shutil.copy2(s, d)
        if not os.path.isdir(os.path.join(self.package_folder,
                                          "site-packages", "airthings")):
            raise ConanException("airthings missing in package")

    def package_info(self):
        sp = os.path.join(self.package_folder, "site-packages")
        self.output.info(f"PYTHONPATH={sp}")
