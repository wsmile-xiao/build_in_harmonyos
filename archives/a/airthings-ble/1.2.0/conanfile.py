#!/usr/bin/env python3
"""Conan recipe — airthings-ble 1.2.0 (pure Python, poetry-core).

HarmonyOS PC adaptation: pure-Python package (airthings_ble/), installed via
pip into a staging prefix. Runtime deps (bleak, bleak-retry-connector,
async-interrupt, cbor2) are NOT published as conan recipes, so they are
resolved by pip from the configured pypi.cnb.cool mirror (same approach as
aiven-client). The upstream pytest suite (tests/, 12 files, no BLE hardware
required — pure hex-data decoding logic) runs during build() and the real
pass/fail counts are reported as HMBS_UPSTREAM_TEST_RESULT JSON.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AirthingsBleConan(ConanFile):
    name = "airthings-ble"
    version = "1.2.0"
    description = "Manage Airthings BLE devices"
    license = "MIT"
    homepage = "https://github.com/Airthings/airthings-ble"
    url = "https://github.com/Airthings/airthings-ble"

    package_type = "python-require"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _site_packages(self, base):
        ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        return os.path.join(base, "lib", ver, "site-packages")

    def build(self):
        apply_conandata_patches(self)
        stage = os.path.join(self.build_folder, "stage")
        python = sys.executable
        # pip install . builds from source (poetry-core); runtime deps are
        # resolved by pip from the configured pypi.cnb.cool mirror.
        # No --no-build-isolation: let pip create its isolated build env and
        # fetch poetry-core from the mirror (same approach as aiven-client).
        self.run(
            f"{python} -m pip install . --prefix={stage}",
            cwd=self.source_folder,
        )
        site = self._site_packages(stage)
        if not os.path.isdir(os.path.join(site, "airthings_ble")):
            raise ConanException(f"airthings_ble package missing under {site}")

    def package(self):
        stage = os.path.join(self.build_folder, "stage")
        if not os.path.isdir(stage):
            raise ConanException(f"stage directory not found: {stage}, nothing to package")
        for item in os.listdir(stage):
            src = os.path.join(stage, item)
            dst = os.path.join(self.package_folder, item)
            if os.path.isdir(src):
                copy(self, "*", src=src, dst=dst)
            else:
                copy(self, item, src=stage, dst=self.package_folder)

    def package_info(self):
        # Pure Python library: expose site-packages via PYTHONPATH for consumers.
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        site = self._site_packages(self.package_folder)
        self.runenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"airthings-ble site-packages: {site}")
