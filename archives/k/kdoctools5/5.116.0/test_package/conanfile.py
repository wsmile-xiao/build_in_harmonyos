#!/usr/bin/env python3
"""HarmonyOS consumer test for the packaged meinproc5 executable."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment


class KDocTools5TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "The kdoctools5 test_package must run on HarmonyOS"
            )
        if not can_run(self):
            raise ConanInvalidConfiguration(
                "The HarmonyOS DocBook runtime test requires a native OHOS runner"
            )

        package = self.dependencies["kdoctools5"]
        meinproc = os.path.join(package.package_folder, "bin", "meinproc5")
        if not os.path.isfile(meinproc):
            raise ConanException("packaged meinproc5 is missing: " + meinproc)

        env = Environment()
        if os.path.isdir("/system/lib64"):
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        for dependency in self.dependencies.values():
            if dependency and dependency.package_folder:
                lib_dir = os.path.join(dependency.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    env.prepend_path("LD_LIBRARY_PATH", lib_dir)
        env.define("QT_QPA_PLATFORM", "offscreen")

        script = os.path.join(self.source_folder, "test_ohos_docbook.py")
        command = "python3 {} {} {}".format(
            shlex.quote(script),
            shlex.quote(meinproc),
            shlex.quote(package.package_folder),
        )
        with env.vars(self).apply():
            self.run(command)
