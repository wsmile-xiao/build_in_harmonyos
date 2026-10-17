#!/usr/bin/env python3
"""Conan test_package — wiliki 0.6.2 (Conan L1 official test).

wiliki is a pure-Scheme wiki engine; there is no C binary to run.  The L1
test loads the installed wiliki module through gosh and exercises a real
public API (wiliki-parse-string) so the package content is verified
(R34: substantive dependency on the tested package).
"""
import os

from conan import ConanFile
from conan.tools.files import copy
from conan.tools.env import Environment


class WilikiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # gosh runtime comes from the gauche dependency.
        self.requires("gauche/0.9.15.2")

    def generate(self):
        # Rebuild the run environment: gauche's bin (gosh on PATH) plus the
        # module search paths of both gauche and the installed wiliki site lib.
        env = Environment()
        if self.dependencies.get("gauche"):
            env.compose_env(self.dependencies["gauche"].runenv_info)
        if self.dependencies.get("wiliki"):
            site_lib = os.path.join(
                self.dependencies["wiliki"].package_folder,
                "share", "gauche-0.98", "site", "lib",
            )
            env.append_path("GAUCHE_LOAD_PATH", site_lib)
        env.vars(self).save_script("conanrun")

    def build(self):
        # Nothing to compile for a pure-Scheme test; the assertions run in
        # test() below via gosh.
        pass

    def test(self):
        # Run the .sh entry (L0c requires a recognized test source extension);
        # it executes gosh with test_wiliki.scm which asserts on wiliki-parse-string.
        script = os.path.join(self.source_folder, "test_wiliki.sh")
        self.run(f"sh {script}", env="conanrun")
