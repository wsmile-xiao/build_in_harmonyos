#!/usr/bin/env python3
"""Conan test_package — acf-kamailio 0.10.0 (Alpine Configuration Framework Kamailio module).

L1 official test: verifies the pure-Lua ACF Kamailio module is packaged correctly.

The module ships:
  - kamailio-controller.lua  (dispatcher controller)
  - kamailio-model.lua       (Kamailio configuration model)
  - kamailio.menu / kamailio.roles (ACF menu and role definitions)
  - kamailio-listfiles-html.lsp   (file listing view)
  - kamailio-listusers-html.lsp   (user listing view)
  - kamailio-searchdatabase-html.lsp (database search view)
  - kamailio-edit-html.lsp    (materialized from acf-core filedetails-html.lsp)
  - kamailio-status-html.lsp  (materialized from acf-core status-html.lsp)

This test verifies the packaged files exist and the Lua sources are
syntactically valid (luac -p). It does NOT require a running Kamailio —
that would be an L2 integration test.
"""
import os
from pathlib import Path

from conan import ConanFile


class AcfKamailioTestConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate the acf-kamailio package root via Conan 2 dependencies API.
        pkg_root = None
        try:
            dep = self.dependencies.get("acf-kamailio")
            if dep and dep.package_folder:
                pkg_root = Path(dep.package_folder)
        except (KeyError, AttributeError, TypeError) as e:
            self.output.warning(f"Could not get acf-kamailio package_folder via dependencies API: {e}")

        test_script = Path(__file__).parent / "test_acf_kamailio.sh"
        if pkg_root:
            os.environ["ACF_KAMAILIO_PKG_ROOT"] = str(pkg_root)
        self.run(f'sh {test_script}')
