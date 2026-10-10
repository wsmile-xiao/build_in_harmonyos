#!/usr/bin/env python3
"""Conan recipe for tqdm 4.70.1 — fast, extensible progress meter.

Pure Python (tqdm/), zero runtime dependencies on non-Windows platforms
(colorama is only pulled in on Windows). HarmonyOS PC adaptation: copytree
staging (awscli WR-008 pattern); the package uses only stdlib plus optional
GUI/notebook integrations that stay import-guarded upstream, so no source
patch is required.

R38 note: upstream setup declares console_scripts entry point "tqdm"
(tqdm.cli:main / tqdm.main), but the CLI is a thin progress-bar renderer that
is not part of any declared consumer workflow in this port; the library API
(tqdm.tqdm/trange) is what lastversion consumes. The bin/ payload is not
installed — library only, hence no commands.json and no cpp_info.bindirs.
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches, export_conandata_patches, get)


class TqdmConan(ConanFile):
    name = "tqdm"
    version = "4.70.1"
    package_type = "python-require"
    license = "MPL-2.0 AND MIT"
    homepage = "https://github.com/tqdm/tqdm"
    description = "Fast, extensible progress meter for Python and CLI"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    settings = "os", "arch", "compiler", "build_type"

    # PyPI requires_dist: colorama; platform_system == "Windows" — not
    # applicable on OHOS (platform_system != "Windows"); extras (discord/
    # slack/telegram/notebook) not enabled.

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"]["tqdm"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        staging = os.path.join(self.build_folder, "tqdm-stage")
        shutil.rmtree(staging, ignore_errors=True)
        src_pkg = os.path.join(self.source_folder, "tqdm")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"tqdm package missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(staging, "tqdm"),
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    def package(self):
        staging = os.path.join(self.build_folder, "tqdm-stage")
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        shutil.copytree(
            os.path.join(staging, "tqdm"), os.path.join(site, "tqdm"),
            ignore=shutil.ignore_patterns("__pycache__"))

        # upstream tqdm/version.py resolves __version__ via
        # importlib.metadata.version("tqdm") unguarded and falls back to
        # "UNKNOWN" when no dist is found — the copytree port must ship a
        # minimal dist-info (equivalent of what pip install would leave
        # behind; cachecontrol recipe precedent), otherwise a clean
        # environment reports UNKNOWN and version assertions fail
        dist_info = os.path.join(site, "tqdm-4.70.1.dist-info")
        os.makedirs(dist_info, exist_ok=True)
        with open(os.path.join(dist_info, "METADATA"), "w", newline="\n") as f:
            f.write("Metadata-Version: 2.1\n"
                    "Name: tqdm\n"
                    "Version: 4.70.1\n"
                    "Summary: Fast, Extensible Progress Meter\n")
        with open(os.path.join(dist_info, "WHEEL"), "w", newline="\n") as f:
            f.write("Wheel-Version: 1.0\n"
                    "Generator: conan-copytree-port\n"
                    "Root-Is-Purelib: true\n"
                    "Tag: py3-none-any\n")

        src_lic = os.path.join(self.source_folder, "LICENCE")
        if os.path.isfile(src_lic):
            lic_dir = os.path.join(self.package_folder, "licenses")
            os.makedirs(lic_dir, exist_ok=True)
            shutil.copy2(src_lic, os.path.join(lic_dir, "LICENCE"))

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver,
                            "site-packages")
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
