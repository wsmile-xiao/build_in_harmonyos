#!/usr/bin/env python3
"""Conan test_package for todo-txt 2.13.0.

Runs a real consumer smoke test against the packaged todo.sh CLI.
"""
import os
import shutil

from conan import ConanFile


class TodotxtTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["todo-txt"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        config_file = os.path.join(dep.package_folder, "etc", "todo", "config")
        todo_cmd = os.path.join(bin_dir, "todo.sh")
        bash_path = shutil.which("bash")
        if not bash_path:
            raise Exception("todo-txt test_package requires bash to run test_todo_txt.sh")

        self.run(
            f'cd "{self.source_folder}" && '
            f'PATH="{bin_dir}:$PATH" '
            f'TODOTXT_TEST_CMD="{todo_cmd}" '
            f'TODOTXT_TEST_CONFIG="{config_file}" '
            f'"{bash_path}" test_todo_txt.sh',
            env="conanrun",
        )
