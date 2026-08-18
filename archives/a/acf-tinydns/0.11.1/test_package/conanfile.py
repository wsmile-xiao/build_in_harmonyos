#!/usr/bin/env python3
"""Conan test_package — acf-tinydns 0.11.1

L1 smoke test: verify the ACF app module files are installed in the package
(tinydns*.lua controllers/model, *.lsp html templates, roles, menu) and that
each .lua file is syntactically valid Lua.

L0d gate: test() must call self.run() to execute a real test program —
the shell script test_tinydns.sh verifies the installed module files.
"""
import os
import shutil

from conan import ConanFile


class AcfTinydnsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder

        # L0d: run a real test program via self.run() — test_tinydns.sh
        # verifies the installed ACF module files (incl. dangling symlinks
        # via -L, matching upstream cp -a semantics).
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        script = os.path.join(self.source_folder, "test_tinydns.sh")
        self.run(
            f'"{bash}" "{script}" "{pkg_folder}"',
            env="conanrun",
        )
