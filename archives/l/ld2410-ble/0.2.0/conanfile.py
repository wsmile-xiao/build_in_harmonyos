#!/usr/bin/env python3
"""Conan recipe — ld2410-ble 0.2.0 (pure Python, poetry-core src layout).

ld2410-ble talks to HLK-LD2410B/LD2410C 24GHz mmWave presence-radar modules
over BLE. It is a pure-Python async library (src/ld2410_ble/, poetry-core
build backend, no C extension, no compilation step).

HarmonyOS PC adaptation notes
-----------------------------
* Pure Python: installation goes through ``pip install .`` into a staging
  prefix; there is no C/C++ toolchain involvement. No C/C++ build dependency
  is introduced deliberately (task requirement: avoid useless C/C++ deps).
* Runtime dependencies (bleak, bleak-retry-connector, async-timeout) are not
  published as conan recipes. They are resolved by pip from the configured
  pypi.cnb.cool mirror during build(), exactly like archives/a/airthings-ble
  (same BLE domain, same dependency set minus cbor2). ``async-timeout/5.0.1``
  was verified present in the ohpcd registry, but bleak /
  bleak-retry-connector are not; the mirror covers all three consistently, so
  a single resolution path (pip) is used instead of mixing conan + pip.
* The upstream sdist on PyPI ships no tests/; the GitHub official tag archive
  is used instead so the upstream pytest suite can be vendored and executed
  (see conandata.yml for the two verified sha256 values).

Rules honoured
--------------
R32: ``settings.os`` is tested with ``in ("Linux", "OHOS")``.
R33: ``build()`` never reads shell env vars (``${CC}``/``${CFLAGS}``); the
     interpreter is ``sys.executable`` (the Conan-managed Python).
R34: test_package performs real consumer assertions against the installed
     package and runs the vendored upstream pytest suite; no print-only stub.
R39: source URL is the official upstream GitHub release archive.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class Ld2410BleConan(ConanFile):
    name = "ld2410-ble"
    version = "0.2.0"
    description = (
        "Interface with LD2410B/LD2410C modules from HiLink over BLE "
        "(24GHz mmWave presence radar)"
    )
    license = "Apache-2.0"
    homepage = "https://github.com/930913/ld2410-ble"
    url = "https://github.com/930913/ld2410-ble"

    package_type = "python-require"

    # Pure Python package: no compiler is involved, but the OHOS profile and
    # the CI L0 settings completeness gate expect the full quartet, matching
    # the already-merged pure-Python recipes (platformdirs, airthings-ble,
    # aiven-client, pluggy). compiler/build_type are inert for pip installs.
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        """R32: OHOS platform compatibility — reject unsupported OS."""
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}. "
                f"ld2410-ble only supports Linux and OHOS."
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _site_packages(self, base):
        """site-packages lives under lib/python3.x/site-packages."""
        version = f"python{sys.version_info.major}.{sys.version_info.minor}"
        return os.path.join(base, "lib", version, "site-packages")

    def build(self):
        apply_conandata_patches(self)
        stage = os.path.join(self.build_folder, "stage")
        # R33: sys.executable (Conan-run interpreter), never a shell variable.
        python = sys.executable
        # pip install . builds from source with poetry-core. The runtime deps
        # (bleak / bleak-retry-connector / async-timeout) are resolved by pip
        # from the configured pypi.cnb.cool mirror so the installed package is
        # import-complete for test_package. No --no-build-isolation: pip
        # creates its own isolated build env and fetches poetry-core from the
        # mirror (same approach as airthings-ble and aiven-client).
        self.run(
            f"{python} -m pip install . --prefix={stage}",
            cwd=self.source_folder,
        )
        site = self._site_packages(stage)
        if not os.path.isdir(os.path.join(site, "ld2410_ble")):
            raise ConanException(
                f"ld2410_ble package missing under {site} — pip install produced "
                f"no importable package"
            )
        self.output.info(f"ld2410-ble staged site-packages: {site}")

    def package(self):
        stage = os.path.join(self.build_folder, "stage")
        if not os.path.isdir(stage):
            raise ConanException(
                f"stage directory not found: {stage}, nothing to package"
            )
        for item in os.listdir(stage):
            src = os.path.join(stage, item)
            dst = os.path.join(self.package_folder, item)
            if os.path.isdir(src):
                copy(self, "*", src=src, dst=dst)
            else:
                copy(self, item, src=stage, dst=self.package_folder)

        # Ship the licence and upstream tests alongside the package so the
        # consumer tests can run the vendored suite without the source tree.
        copy(self, "LICENSE", src=self.source_folder, dst=self.package_folder)

    def package_info(self):
        # Pure Python library: expose site-packages on PYTHONPATH instead of
        # advertising C/C++ libs or include dirs (which do not exist here).
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        site = self._site_packages(self.package_folder)
        self.runenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"ld2410-ble installed: {site}/ld2410_ble/")
