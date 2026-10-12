#!/usr/bin/env python3
"""Consumer tests for the packaged SPLAT! command-line tools."""

import os

from conan import ConanFile


class SplatTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dependency = self.dependencies["splat"]
        bindir = dependency.cpp_info.bindirs[0]
        if not os.path.isabs(bindir):
            bindir = os.path.join(dependency.package_folder, bindir)

        integration = os.path.join(self.source_folder, "test_splat.sh")
        self.run('sh "%s" "%s"' % (integration, bindir), env="conanrun")

        if str(self.settings.os) == "OHOS":
            ohos_test = os.path.join(self.source_folder, "test_ohos.sh")
            self.run('sh "%s" "%s"' % (ohos_test, bindir), env="conanrun")
