#!/usr/bin/env python3
"""Conan test_package — debichem (Debian Pure Blend metadata package).

Honest validation (no compiled binary exists to run):
  - packaged file layout (12 task files, tasksel desc, registry.json, license)
  - tasksel desc structure: 1 parent Task 'debichem' + 12 children with
    'Key: debichem-<task>' exactly matching the packaged tasks/ dir
  - registry.json (derived from tasks/ by the recipe) matches each task file's
    Task:/Description: title and Deb822 Depends/Suggests fields, re-derived
    here from the packaged files (cross-check, not a self-tautology).
These are package/data validations (upstream blend has no test suite).
"""
import os

from conan import ConanFile


class DebichemTestConan(ConanFile):
    settings = None
    options = None
    default_options = None

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["debichem"].package_folder
        script = os.path.join(self.source_folder, "test_debichem.py")
        self.run(f"python3 {script} {pkg}", env="conanrun")
