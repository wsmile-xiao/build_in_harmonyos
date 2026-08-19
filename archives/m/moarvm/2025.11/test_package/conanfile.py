#!/usr/bin/env python3
"""Consumer tests for the packaged MoarVM executable and libuv affinity API."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class MoarvmTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_affinity.c", "test.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dependency = self.dependencies["moarvm"]
        compiler = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c", "clang")
        include_dir = os.path.join(dependency.package_folder, "include")
        library_dir = os.path.join(dependency.package_folder, "lib")
        source = os.path.join(self.source_folder, "test_affinity.c")
        output = os.path.join(self.build_folder, "test_affinity")
        self.run(
            f'"{compiler}" "{source}" -I"{include_dir}" '
            f'-L"{library_dir}" -lmoar -o "{output}"',
            env="conanbuild",
        )

    def test(self):
        if not can_run(self):
            return
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{shell} "{os.path.join(self.source_folder, "test.sh")}"', env="conanrun")
        self.run(os.path.join(self.build_folder, "test_affinity"), env="conanrun")
