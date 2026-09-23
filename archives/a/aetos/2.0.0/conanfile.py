#!/usr/bin/env python3
"""Conan recipe for aetos 2.0.0 — OpenStack Prometheus multi-tenancy proxy.

Pure-Python OpenStack service (PyPI sdist). Port follows the python-require
template (cycler/zipp/awscli precedent): source download + build() staging
copytree under build_folder + package() copy of the aetos/ package and
shipped configs into lib/python3.12/site-packages and etc/.

Runtime deps (PKG-INFO Requires-Dist, 14 entries: pbr, keystonemiddleware,
lxml, oslo.config/i18n/log/policy/middleware/utils, PasteDeploy, Paste,
pecan, WSME, python-observabilityclient) are NOT declared as Conan requires:
none of the OpenStack-specific packages exist in this repo yet (R36 gate —
declaring unpublished deps fails L0i). The missing chain is recorded in
README/notes/MANIFEST and the consumer test degrades honestly instead of
faking imports.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get


class AetosConan(ConanFile):
    name = "aetos"
    version = "2.0.0"
    package_type = "python-require"
    license = "Apache-2.0"
    homepage = "https://www.openstack.org/"
    description = (
        "Aetos is a reverse proxy for enforcing openstack "
        "multi-tenancy for Prometheus."
    )
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"
    # Upstream Requires-Dist audit (PKG-INFO, 14 entries):
    #   pbr>=6.0.0 | keystonemiddleware>=5.1.0 | lxml>=2.3
    #   oslo.config>=6.8.0 | oslo.i18n>=1.5.0 | oslo.log>=4.3.0
    #   oslo.policy>=4.5.0 | PasteDeploy>=1.5.0 | Paste>=3.10
    #   pecan>=0.8.0 | oslo.middleware>=3.22.0 | oslo.utils>=4.7.0
    #   WSME>=0.12.1 | python-observabilityclient>=1.1.0
    # R36: none of the OpenStack-specific dists have recipes in this repo
    # (only pbr/7.0.3 recipe dir exists, without published manifest), so
    # requires stays empty. Declaring them would fail the dependency gate.
    requires = []

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # Pure Python: copytree source to a staging dir under build_folder
        # (build-folder staging, not a hardcoded absolute path, so parallel
        # builds cannot clobber each other — awscli WR-008 lesson).
        staging = os.path.join(self.build_folder, "aetos-stage")
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder,
            staging,
            ignore=shutil.ignore_patterns(
                ".git", ".github", ".tox", ".venv", "doc", "releasenotes",
                "devstack", "*.egg-info", "__pycache__", "*.pyc",
                ".coveragerc", ".stestr.conf", ".zuul.yaml",
                ".pre-commit-config.yaml", "tox.ini",
                "test-requirements.txt",
            ),
        )

    def package(self):
        staging = os.path.join(self.build_folder, "aetos-stage")
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        src_pkg = os.path.join(staging, "aetos")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"aetos package missing: {src_pkg}")
        pyver = "python3.12"
        site = os.path.join(
            self.package_folder, "lib", pyver, "site-packages"
        )
        os.makedirs(site, exist_ok=True)
        shutil.copytree(
            src_pkg,
            os.path.join(site, "aetos"),
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        # Ship WSGI/paste configs and PKG metadata for consumer validation.
        for fname in ("PKG-INFO", "setup.cfg"):
            src = os.path.join(staging, fname)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(site, f"aetos-{fname}"))
        etc_src = os.path.join(staging, "etc", "aetos")
        if os.path.isdir(etc_src):
            etc_dst = os.path.join(self.package_folder, "etc", "aetos")
            os.makedirs(etc_dst, exist_ok=True)
            for entry in os.listdir(etc_src):
                s = os.path.join(etc_src, entry)
                d = os.path.join(etc_dst, entry)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
        api_ini = os.path.join(staging, "aetos", "api-paste.ini")
        if not os.path.isfile(api_ini):
            raise ConanException(f"api-paste.ini missing: {api_ini}")

    def package_info(self):
        # python-require type — runtime env provided by conanrun.
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["lib/python3.12/site-packages"]
