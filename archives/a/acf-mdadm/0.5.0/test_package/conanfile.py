#!/usr/bin/env python3
"""Conan test_package for acf-mdadm 0.5.0 (pure Lua ACF module).

R34: the test must exercise the packaged payload. acf-mdadm ships Lua
controllers/models/HTML views under share/acf/app/mdadm — verify the key
files exist (no compiled binary to run for a pure-data module).
"""
import os

from conan import ConanFile


class AcfMdadmTestConan(ConanFile):
    settings = "os", "arch", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["acf-mdadm"].package_folder
        app_dir = os.path.join(pkg, "share", "acf", "app", "mdadm")
        required = [
            "mdadm-controller.lua",
            "mdadm-model.lua",
            "mdadm-details-html.lsp",
            "mdadm.menu",
            "mdadm.roles",
        ]
        missing = [f for f in required if not os.path.isfile(os.path.join(app_dir, f))]
        assert not missing, f"acf-mdadm missing files: {missing}"
        # R34/L0d: exercise the packaged payload — verify each Lua module is
        # non-empty and parseable as text (pure-data module, no binary to run).
        for f in required:
            path = os.path.join(app_dir, f)
            self.run(f'sh -c "test -s \\"{path}\\" && grep -q . \\"{path}\\""')
        self.output.info(f"acf-mdadm module files verified in {app_dir}")
