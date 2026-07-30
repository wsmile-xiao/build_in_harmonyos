#!/usr/bin/env python3
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class AnyenvTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["anyenv"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        anyenv = os.path.join(bin_dir, "anyenv")
        bash = shutil.which("bash") or os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "bash"
        root = os.path.join(self.build_folder, "anyenv-root")
        os.makedirs(root, exist_ok=True)

        ceiling = os.path.dirname(root)
        env = f'ANYENV_ROOT="{root}" GIT_CEILING_DIRECTORIES="{ceiling}" PATH="{bin_dir}:$PATH"'
        self.run(f'cd "{self.source_folder}" && {env} "{bash}" test.sh "{anyenv}" "{root}"', env="conanrun")
        self.run(f'{env} "{anyenv}" --version', env="conanrun")
        self.run(f'test "$({env} "{anyenv}" root)" = "{root}"', env="conanrun")
        self.run(f'{env} "{anyenv}" commands | grep -E "(^|[[:space:]])root($|[[:space:]])"', env="conanrun")
