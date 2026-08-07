#!/usr/bin/env python3
"""Conan consumer test for rdiff-backup 2.2.6."""

import os
import glob
import sys

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class RdiffBackupTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def configure(self):
        self.settings.rm_safe("os.version")

    def test(self):
        if str(self.settings.os) == "OHOS":
            self._test_ohos_artifacts()
            return
        if not can_run(self):
            return

        test_script = os.path.join(self.source_folder, "test_rdiff_backup.py")
        env = Environment()
        env.define("RDIFF_BACKUP_TEST_TMP", self.build_folder)
        for path in ("/bin", "/usr/bin", "/sbin", "/usr/sbin"):
            env.append_path("PATH", path)
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" "{test_script}"', env="conanrun")

    def _test_ohos_artifacts(self):
        package_folder = str(self.dependencies[self.tested_reference_str].package_folder)
        script = os.path.join(package_folder, "bin", "rdiff-backup")
        if not os.path.isfile(script):
            raise AssertionError("rdiff-backup console script is missing: {}".format(script))
        with open(script, "rb") as handle:
            script_data = handle.read()
        if b"console_scripts" not in script_data or b"rdiff-backup" not in script_data:
            raise AssertionError("rdiff-backup console script does not reference the console entry point")

        site_packages = self._site_packages(package_folder)
        entry_points = glob.glob(os.path.join(site_packages, "rdiff_backup*.egg-info", "entry_points.txt"))
        entry_points += glob.glob(os.path.join(site_packages, "rdiff_backup*.dist-info", "entry_points.txt"))
        if len(entry_points) != 1:
            raise AssertionError(
                "expected one rdiff-backup entry_points.txt, found {}".format(len(entry_points))
            )
        with open(entry_points[0], "rb") as handle:
            entry_data = handle.read()
        if b"rdiff-backup = rdiffbackup.run:main" not in entry_data:
            raise AssertionError("rdiff-backup entry_points.txt does not map to rdiffbackup.run:main")

        checks = {
            "C": b"PyInit_C",
            "_librsync": b"PyInit__librsync",
        }
        for module, init_symbol in checks.items():
            pattern = os.path.join(
                site_packages,
                "rdiff_backup",
                "{}.cpython-*-aarch64-linux-ohos.so".format(module),
            )
            matches = glob.glob(pattern)
            if len(matches) != 1:
                raise AssertionError(
                    "expected one rdiff_backup.{} extension, found {}".format(
                        module, len(matches)
                    )
                )
            self._check_signed_extension(matches[0], init_symbol)
        self.output.info("rdiff-backup OHOS artifact checks passed")

    def _site_packages(self, package_folder):
        candidates = glob.glob(os.path.join(package_folder, "lib", "python*", "site-packages"))
        candidates += glob.glob(os.path.join(package_folder, "lib", "python", "site-packages"))
        for path in candidates:
            if os.path.isdir(os.path.join(path, "rdiff_backup")):
                return path
        raise AssertionError("rdiff_backup site-packages directory was not found")

    def _check_signed_extension(self, path, init_symbol):
        if not os.path.isfile(path):
            raise AssertionError("extension file is missing: {}".format(path))
        with open(path, "rb") as handle:
            data = handle.read()
        if not data.startswith(b"\x7fELF"):
            raise AssertionError("extension is not ELF: {}".format(path))
        if b".codesign" not in data:
            raise AssertionError("extension is missing OHOS .codesign section: {}".format(path))
        if init_symbol not in data:
            raise AssertionError(
                "extension is missing expected init symbol {}: {}".format(
                    init_symbol.decode("ascii"), path
                )
            )
