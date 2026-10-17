#!/usr/bin/env python3
"""Consumer test for every Omins LADSPA module and descriptor."""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv


class OminsTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("ladspa-sdk/1.17")

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def _c_compiler(self):
        configured = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(configured, str):
            try:
                configured = json.loads(configured.replace("'", '"'))
            except json.JSONDecodeError:
                configured = {}
        candidate = configured.get("c") if isinstance(configured, dict) else None
        if candidate and (os.path.isabs(candidate) or shutil.which(candidate)):
            return candidate
        candidate = shutil.which("clang")
        if candidate:
            return candidate
        raise ConanException("unable to locate the configured C compiler")

    def test(self):
        if not self.conf.get("tools.build:skip_test", default=False):
            plugin_dir = os.path.join(
                self.dependencies["omins"].package_folder, "lib", "ladspa"
            )
            include_dir = os.path.join(
                self.dependencies["ladspa-sdk"].package_folder, "include"
            )
            source = os.path.join(self.source_folder, "src", "test_omins_host.c")
            executable = os.path.join(self.build_folder, "test_omins_host")
            self.run(
                '"{}" -std=c11 -Wall -Wextra -Werror -I"{}" "{}" '
                '-o "{}" -ldl -lm'.format(
                    self._c_compiler(), include_dir, source, executable
                ),
                env="conanbuild",
            )
            self.run(
                '"{}" "{}"'.format(executable, plugin_dir),
                env="conanrun",
            )
