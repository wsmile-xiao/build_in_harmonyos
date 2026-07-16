#!/usr/bin/env python3
"""Conan recipe for todo-txt 2.13.0 — pure Bash todo.txt CLI.

The upstream release is a script-only distribution containing todo.sh,
todo.cfg, and bash completion. No compilation is required; packaging copies
those files into bin/, etc/todo/, and share/bash-completion/completions/.

R32: OHOS adaptation is path/config driven and does not gate on Linux-only OS checks.
R34: test_package exercises the packaged CLI by adding, listing, completing,
and archiving todo.txt tasks.
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class TodotxtConan(ConanFile):
    name = "todo-txt"
    version = "2.13.0"
    description = "Simple plaintext todo list manager"
    license = "GPL-3.0-only"
    homepage = "https://github.com/todotxt/todo.txt-cli"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"

    settings = "os", "arch"
    package_type = "application"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # No build step: upstream ships portable Bash scripts.
        pass

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        config_dir = os.path.join(self.package_folder, "etc", "todo")
        completion_dir = os.path.join(self.package_folder, "share", "bash-completion", "completions")

        copy(self, "todo.sh", src=self.source_folder, dst=bin_dir, keep_path=False)
        copy(self, "todo.cfg", src=self.source_folder, dst=config_dir, keep_path=False)
        copy(self, "todo_completion", src=self.source_folder, dst=completion_dir, keep_path=False)

        config_path = os.path.join(config_dir, "todo.cfg")
        canonical_config_path = os.path.join(config_dir, "config")
        if os.path.isfile(config_path) and not os.path.exists(canonical_config_path):
            os.replace(config_path, canonical_config_path)

        todo_sh = os.path.join(bin_dir, "todo.sh")
        if os.path.isfile(todo_sh):
            os.chmod(todo_sh, os.stat(todo_sh).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.define_path("TODOTXT_GLOBAL_CFG_FILE", os.path.join(self.package_folder, "etc", "todo", "config"))
