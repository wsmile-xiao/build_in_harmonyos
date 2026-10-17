#!/usr/bin/env python3
"""Consumer test: load rwm.so and parse an rwm-enabled slapd config."""

import glob
import os
import sys

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv
from conan.tools.files import load, save


class OpenLdapOverlayRwmTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def build(self):
        package = self.dependencies["openldap-overlay-rwm"].package_folder
        module_dir = os.path.join(package, "libexec", "openldap")
        candidates = sorted(glob.glob(os.path.join(module_dir, "rwm.so*")))
        if not candidates:
            raise RuntimeError("packaged rwm module was not found")
        core_schema = os.path.join(
            package, "etc", "openldap", "schema", "core.schema"
        )
        if not os.path.isfile(core_schema):
            raise RuntimeError("packaged OpenLDAP core schema was not found")

        preferred = os.path.join(module_dir, "rwm.so")
        module_file = "rwm.so" if os.path.exists(preferred) else os.path.basename(candidates[0])
        template = load(
            self, os.path.join(self.source_folder, "slapd-rwm.conf.in")
        )
        config = template.replace("@CORE_SCHEMA@", core_schema)
        config = config.replace("@MODULE_DIR@", module_dir)
        config = config.replace("@MODULE_FILE@", module_file)
        save(self, os.path.join(self.build_folder, "slapd-rwm.conf"), config)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: rwm runtime configuration test skipped")
            return
        package = self.dependencies["openldap-overlay-rwm"].package_folder
        module_dir = os.path.join(package, "libexec", "openldap")
        candidates = sorted(glob.glob(os.path.join(module_dir, "rwm.so*")))
        if not candidates:
            raise RuntimeError("packaged rwm module was not found")
        slapd = os.path.join(package, "libexec", "slapd")
        config = os.path.join(self.build_folder, "slapd-rwm.conf")
        test_script = os.path.join(self.source_folder, "test_rwm.py")
        self.run(
            f'"{sys.executable}" "{test_script}" "{slapd}" '
            f'"{candidates[0]}" "{config}"',
            env="conanrun",
        )
