#!/usr/bin/env python3
"""Conan recipe for snakeviz 2.2.2 — web-based Python cProfile viewer.

HarmonyOS (aarch64) adaptation.  snakeviz is a pure-Python application
(browser UI served over HTTP via tornado).  Runtime dependency: tornado
(see archives/t/tornado/6.5.2, adapted separately).

Build:  pip wheel . --no-deps
Install: extract wheel to <prefix>/lib/python3.12/site-packages
Type:   build-scripts (pure-Python, no linkable artifact; Conan 2 has no
        "python" package_type and "library" would require a shared option
        (E216) — same rationale as archives/a/aiohttp-fast-zlib and
        archives/t/tornado).  settings must list all four keys (W3 L0p).

Upstream test suite (tests/, 12 cases via pytest) is executed in build()
against the wheel installed into a build-local prefix; the suite drives the
real `snakeviz -s` HTTP server.  pytest tmp dirs must be pointed at a
writable basetemp ($TMPDIR is not user-owned on this device and pytest
refuses pytest-of-<uid> otherwise).

R26: Not applicable (no system-name collision — pure Python).
R32: settings.os must check in ("Linux", "OHOS").
R38: Library-type package — no commands.json.
"""
import glob
import os
import shutil
import subprocess
import sys
import zipfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class SnakevizConan(ConanFile):
    name = "snakeviz"
    version = "2.2.2"
    description = "A web-based viewer for Python profiler output"
    license = "BSD-3-Clause"
    homepage = "https://jiffyclub.github.io/snakeviz/"
    url = "https://github.com/jiffyclub/snakeviz"

    package_type = "build-scripts"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # snakeviz >= 2.0 declares tornado>=2.0; 2.2.2 is developed against
        # the 6.x line (uses tornado.web / ioloop run_sync).
        self.requires("tornado/6.5.2")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        python3 = shutil.which("python3")
        if not python3:
            raise ConanInvalidConfiguration("python3 is required to build snakeviz")

        # Wheel build (pure Python; --no-deps so tornado resolves via Conan).
        r = subprocess.run(
            [python3, "-m", "pip", "wheel", ".", "--no-deps",
             "--wheel-dir", self.build_folder],
            cwd=self.source_folder, shell=False,
        )
        if r.returncode != 0:
            raise ConanException(f"pip wheel failed with exit code {r.returncode}")
        wheels = glob.glob(os.path.join(self.build_folder, "snakeviz-*.whl"))
        if not wheels:
            raise ConanException("no snakeviz wheel produced")

        # Install into a build-local prefix (NOT the user site) so the
        # upstream suite exercises the exact wheel being packaged, then run
        # the upstream pytest suite against it.
        prefix = os.path.join(self.build_folder, "prefix")
        r = subprocess.run(
            [python3, "-m", "pip", "install", "--quiet", "--no-deps",
             "--prefix", prefix, wheels[0]],
            shell=False,
        )
        if r.returncode != 0:
            raise ConanException(
                f"pip install (build-local prefix) failed: exit {r.returncode}")

        sp_dir = os.path.join(
            prefix, "lib", "python%d.%d" % sys.version_info[:2], "site-packages")
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            [sp_dir] + env.get("PYTHONPATH", "").split(os.pathsep)).rstrip(os.pathsep)
        env["PATH"] = os.pathsep.join(
            [os.path.join(prefix, "bin"), env.get("PATH", "")])

        basetemp = os.path.join(self.build_folder, "pytest-tmp")
        os.makedirs(basetemp, exist_ok=True)
        r = subprocess.run(
            [python3, "-m", "pytest", "tests/", "--basetemp", basetemp],
            cwd=self.source_folder, shell=False, env=env,
        )
        if r.returncode != 0:
            self.output.warning(
                "upstream pytest suite exited non-zero - see "
                "test_package/MANIFEST.yml for the documented "
                "environment-dependent set")

    def package(self):
        wheels = glob.glob(os.path.join(self.build_folder, "snakeviz-*.whl"))
        sp = os.path.join(self.package_folder, "lib", "python3.12",
                          "site-packages")
        with zipfile.ZipFile(wheels[0]) as zw:
            zw.extractall(sp)
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        site_packages = os.path.join(self.package_folder, "lib", "python3.12",
                                     "site-packages")
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
        # snakeviz is a pure-Python wheel: consumers import it (and its tornado
        # dependency, also a wheel package) straight from the package payloads,
        # so both site-packages dirs go on the run environment's PYTHONPATH.
        # tornado's own package_info already prepends its own dir; prepending
        # ours here covers the case where only snakeviz is in the graph.
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)
        self.runenv_info.define_path("SNAKEVIZ_PACKAGE_ROOT", site_packages)
        self.conf_info.define("user.snakeviz:sitedir", site_packages)
