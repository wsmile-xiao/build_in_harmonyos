#!/usr/bin/env python3
"""Conan test_package — adwaita-icon-theme 49.0

Verifies:
  1. index.theme exists in share/icons/Adwaita/
  2. Icon size directories exist (16x16, scalable, symbolic)
  3. Cursor directory exists with symlinks
  4. License files exist
  5. .pc file exists with correct name and version
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class AdwaitaIconThemeTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["adwaita-icon-theme"]
        icons_root = os.path.join(dep.package_folder, "share", "icons")
        adwaita_dir = os.path.join(icons_root, "Adwaita")

        self.output.info(f"Adwaita icons dir: {adwaita_dir}")
        errors = []

        # 1. index.theme exists
        index_path = os.path.join(adwaita_dir, "index.theme")
        if os.path.isfile(index_path):
            self.output.info("✓ index.theme found")
        else:
            errors.append("MISSING: index.theme")

        # 2. Icon size directories
        expected_dirs = ("16x16", "scalable", "symbolic")
        for d in expected_dirs:
            dpath = os.path.join(adwaita_dir, d)
            if os.path.isdir(dpath):
                file_count = sum(
                    1 for _ in os.scandir(dpath) if _.is_file() or _.is_dir()
                )
                self.output.info(f"✓ {d}/ exists ({file_count} entries)")
            else:
                errors.append(f"MISSING: {d}/ directory")

        # 3. Cursor directory with symlinks
        cursors_dir = os.path.join(adwaita_dir, "cursors")
        if os.path.isdir(cursors_dir):
            entries = list(os.scandir(cursors_dir))
            symlinks = [e for e in entries if e.is_symlink()]
            files = [e for e in entries if e.is_file()]
            self.output.info(
                f"✓ cursors/ exists ({len(files)} files, {len(symlinks)} symlinks)"
            )
            if len(symlinks) < 10:
                errors.append(
                    f"Expected ≥10 cursor symlinks, found {len(symlinks)}"
                )
        else:
            errors.append("MISSING: cursors/ directory")

        # 4. License files
        licenses_dir = os.path.join(
            dep.package_folder, "share", "licenses", "adwaita-icon-theme"
        )
        for lic in ("COPYING", "COPYING_CCBYSA3", "COPYING_LGPL"):
            lpath = os.path.join(licenses_dir, lic)
            if os.path.isfile(lpath):
                self.output.info(f"✓ {lic} found")
            else:
                errors.append(f"MISSING: {lic}")

        # 5. .pc file
        pc_dir = os.path.join(dep.package_folder, "share", "pkgconfig")
        pc_path = os.path.join(pc_dir, "adwaita-icon-theme.pc")
        if os.path.isfile(pc_path):
            with open(pc_path, "r") as f:
                content = f.read()
            if "adwaita-icon-theme" in content and "49.0" in content:
                self.output.info("✓ .pc file correct")
            else:
                errors.append(".pc file missing expected fields")
        else:
            errors.append("MISSING: adwaita-icon-theme.pc")

        # R34/L0d: use self.run() to verify package on target
        # Count installed icon files as a smoke test
        if can_run(self):
            self.run(
                f'bash -c \'find "{icons_root}" -type f | wc -l\'',
                env="conanrun"
            )
            self.run(
                f'bash -c \'test -f "{index_path}" && echo "index.theme verified"\'',
                env="conanrun"
            )

        if errors:
            for e in errors:
                self.output.error(e)
            raise Exception(f"test_package FAILED: {len(errors)} error(s)")
        else:
            self.output.info(
                "=== adwaita-icon-theme test_package: ALL CHECKS PASSED ==="
            )
