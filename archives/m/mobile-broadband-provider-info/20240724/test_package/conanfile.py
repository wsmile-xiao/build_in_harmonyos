#!/usr/bin/env python3
"""Consumer validation for the architecture-independent
mobile-broadband-provider-info package."""

import os
import shutil
import sys

from conan import ConanFile


class MobileBroadbandProviderInfoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dependency = self.dependencies["mobile-broadband-provider-info"]
        if dependency.ref.version != "20240724":
            raise RuntimeError(
                "unexpected Conan package version: {}".format(dependency.ref.version)
            )
        package_folder = dependency.package_folder
        script = os.path.join(self.recipe_folder, "test_verify.py")
        self.run(
            '"{}" "{}" "{}"'.format(sys.executable, script, package_folder)
        )
        xmllint = shutil.which("xmllint") or "/data/service/hnp/bin/xmllint"
        database = os.path.join(
            package_folder, "share", "mobile-broadband-provider-info",
            "serviceproviders.xml",
        )
        # Upstream xmllint test replayed against the installed tree:
        # --valid resolves serviceproviders.2.dtd from the database's
        # own directory (co-location contract).
        self.run('"{}" --noout --valid "{}"'.format(xmllint, database))
