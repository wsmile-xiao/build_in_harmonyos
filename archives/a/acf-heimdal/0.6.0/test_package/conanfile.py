#!/usr/bin/env python3
"""Conan test_package — acf-heimdal 0.6.0 (Alpine Configuration Framework heimdal module).

L1 official test: verifies the pure-Lua ACF heimdal module is packaged correctly.

The module ships:
  - heimdal-controller.lua   (dispatcher controller)
  - heimdal-model.lua        (Kerberos configuration model)
  - heimdal.menu / heimdal.roles (ACF menu and role definitions)
  - heimdal-klist-html.lsp   (ticket list view template)
  - heimdal-expert-html.lsp  (materialized from acf-core expert-html.lsp)
  - heimdal-status-html.lsp  (materialized from acf-core status-html.lsp)

This test verifies the packaged files exist, the shared views are materialized
as regular files (not dangling symlinks), and the Lua sources are
syntactically valid (luac -p). It does NOT require a running Heimdal KDC —
that would be an L2 integration test.
"""
import os
from pathlib import Path

from conan import ConanFile


class AcfHeimdalTestConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate the acf-heimdal package root via Conan 2 dependencies API.
        pkg_root = None
        try:
            dep = self.dependencies.get("acf-heimdal")
            if dep and dep.package_folder:
                pkg_root = Path(dep.package_folder)
        except (KeyError, AttributeError, TypeError) as e:
            self.output.warning(f"Could not get acf-heimdal package_folder via dependencies API: {e}")

        test_script = Path(__file__).parent / "test_acf_heimdal.sh"
        if pkg_root:
            os.environ["ACF_HEIMDAL_PKG_ROOT"] = str(pkg_root)
        self.run(f'sh {test_script}')
