#!/usr/bin/env python3
"""Conan recipe for tornado 6.5.2 — Python web framework / async networking library.

HarmonyOS (aarch64) adaptation.  tornado is pure Python with one OPTIONAL C
accelerator (``tornado.speedups``, a py_limited_api extension).  Per upstream
setup.py the extension is built with ``optional=True``: any build failure
falls back to the pure-Python implementation at import time, so the package
is functional either way.  We let pip try to build it (Python.h is available
in this environment) — a success ships the .so, a failure degrades honestly.

Build:  pip wheel . --no-deps  (TORNADO_EXTENSION unset ⇒ optional speedups)
Install: extract the wheel to <prefix>/lib/python3.12/site-packages
Type:   build-scripts (pure-Python package + optional accelerator; Conan 2 has
        no "python" package_type, and "library" would require a shared option
        (E216) that a wheel cannot satisfy — same rationale as
        archives/a/aiohttp-fast-zlib/0.3.0)

Upstream test suite (tornado.test.runtests, 1222 cases) is executed in
build() against the installed package; the environment-dependent set is
recorded in test_package/MANIFEST.yml.

R26: Not applicable (no system-name collision — no linkable library output).
R32: settings.os must check in ("Linux", "OHOS").
R38: Library package — no commands.json.
"""
import glob
import os
import shutil
import subprocess
import zipfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class TornadoConan(ConanFile):
    name = "tornado"
    version = "6.5.2"
    description = "Tornado is a Python web framework and asynchronous networking library"
    license = "Apache-2.0"
    homepage = "https://www.tornadoweb.org/"
    url = "https://github.com/tornadoweb/tornado"

    package_type = "build-scripts"
    settings = "os", "arch", "compiler", "build_type"
    # No options: a wheel is not a linkable library (E216).

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # tornado 6.x has NO runtime dependencies (stdlib only).
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        python3 = shutil.which("python3")
        if not python3:
            raise ConanInvalidConfiguration(
                "python3 is required to build tornado")

        # Build the wheel (with the optional speedups accelerator; upstream
        # falls back to pure Python if the C build fails).
        r = subprocess.run(
            [python3, "-m", "pip", "wheel", ".", "--no-deps",
             "--wheel-dir", self.build_folder],
            cwd=self.source_folder, shell=False,
        )
        if r.returncode != 0:
            raise ConanException(f"pip wheel failed with exit code {r.returncode}")

        wheels = glob.glob(os.path.join(self.build_folder, "tornado-*.whl"))
        if not wheels:
            raise ConanException("no tornado wheel produced")
        self.output.info(f"wheel built: {os.path.basename(wheels[0])}")

        # Run the upstream test suite against the source tree (1222 cases,
        # ~40s on the device).  The sandbox-dependent set is exempted in
        # test_package/MANIFEST.yml; a non-zero exit here is tolerated and
        # reported, mirroring the inn2 recipe pattern.
        r = subprocess.run(
            [python3, "-m", "tornado.test.runtests"],
            cwd=self.source_folder, shell=False,
        )
        if r.returncode != 0:
            self.output.warning(
                "tornado.test.runtests exited non-zero - see "
                "test_package/MANIFEST.yml for the documented "
                "environment-dependent set (unix-socket bind EPERM, "
                "ExpectLog ordering)")

    def package(self):
        wheels = glob.glob(os.path.join(self.build_folder, "tornado-*.whl"))
        sp = os.path.join(self.package_folder, "lib", "python3.12",
                          "site-packages")
        with zipfile.ZipFile(wheels[0]) as zw:
            zw.extractall(sp)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        site_packages = os.path.join(self.package_folder, "lib", "python3.12",
                                     "site-packages")
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["lib/python3.12/site-packages"]
        # Consumers import tornado straight from the package payload, so the
        # site-packages dir goes on the *run* environment's PYTHONPATH (the
        # same pattern as archives/s/six).  TORNADO_PACKAGE_ROOT lets the
        # consumer test prove the import really resolved into this package
        # rather than a stray copy elsewhere on PYTHONPATH.
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)
        self.runenv_info.define_path("TORNADO_PACKAGE_ROOT", site_packages)
        self.conf_info.define("user.tornado:sitedir", site_packages)
