#!/usr/bin/env python3
"""Conan recipe — rapt-ble 0.1.2 (pure Python, poetry-core).

HarmonyOS PC adaptation: rapt-ble is a pure-Python package (src/rapt_ble/,
zero C/C++ sources), installed via pip into a private staging prefix that is
shipped verbatim in the conan package. The whole runtime closure
(bluetooth-data-tools, bluetooth-sensor-state-data, home-assistant-bluetooth,
sensor-state-data, habluetooth, bleak, cryptography, cffi, ...) is NOT
published as conan recipes in the ohpcd registry (verified with
`conan download <pkg>/* --only-recipe` against the ohpcd remote: no matching
recipe references), so the dependencies are resolved by pip from the configured
pypi.cnb.cool mirror during build() — same approach as the already-merged
airthings-ble 1.2.0 and aiven-client. `--ignore-installed` keeps the shipped
site-packages self-contained even when the build interpreter already has some
of those distributions installed (this machine ships cffi/cryptography in
/usr/local/lib/python3.12/site-packages).

The upstream pytest suite (tests/, 1 file, 7 cases, pure hex-payload decoding
— no BLE hardware required) is NOT part of the PyPI sdist, therefore the
source is fetched from the official GitHub tag archive
(https://github.com/sairon/rapt-ble/archive/refs/tags/v0.1.2.tar.gz,
sha256 verified) which does contain tests/. The suite is copied into
test_package/tests/ and executed by test_package/conanfile.py, which emits
the real pass/fail counts as HMBS_UPSTREAM_TEST_RESULT.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class RaptBleConan(ConanFile):
    name = "rapt-ble"
    version = "0.1.2"
    description = "Parser for the RAPT Pill hydrometer BLE packets"
    license = "MIT"
    homepage = "https://github.com/sairon/rapt-ble"
    url = "https://github.com/sairon/rapt-ble"

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
        # pip install . builds the wheel from source (poetry-core); the runtime
        # deps are resolved by pip from the configured pypi.cnb.cool mirror.
        # No --no-build-isolation: let pip create its isolated build env and
        # fetch poetry-core from the mirror (same approach as aiven-client).
        # --ignore-installed keeps the staged site-packages self-contained
        # (the build interpreter ships cffi/cryptography of its own).
        self.run(
            f"{python} -m pip install . --prefix={stage} --ignore-installed "
            f"--no-warn-script-location",
            cwd=self.source_folder,
        )
        site = self._site_packages(stage)
        if not os.path.isdir(os.path.join(site, "rapt_ble")):
            raise ConanException(f"rapt_ble package missing under {site}")

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
        self.output.info(f"rapt-ble site-packages: {site}")
