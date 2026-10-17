#!/usr/bin/env python3
"""Conan test_package for ldap2zone 0.2.

Runs the installed ``ldap2zone`` CLI (usage/exit code on missing args,
rejection of a non-LDAP URL — both without touching the network) and
syntax-checks the installed ``ldap2bind`` shell script.
"""
import json
import os

from conan import ConanFile

CHECKS = 3


class Ldap2zoneTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        binary = os.path.join(package_folder, "bin", "ldap2zone")
        bind_script = os.path.join(package_folder, "bin", "ldap2bind")
        script = os.path.join(self.recipe_folder, "test_ldap2zone.sh")
        if not os.path.isfile(binary):
            raise Exception("ldap2zone binary not found: %s" % binary)
        if not os.path.isfile(bind_script):
            raise Exception("ldap2bind script not found: %s" % bind_script)
        self.run('LDAP2ZONE_BIN="%s" LDAP2BIND_FILE="%s" sh "%s"'
                 % (binary, bind_script, script), env="conanrun")
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_ldap2zone.sh (usage/exit code/bad URL/ldap2bind syntax)",
            "discovered": CHECKS,
            "passedCount": CHECKS,
        }))
