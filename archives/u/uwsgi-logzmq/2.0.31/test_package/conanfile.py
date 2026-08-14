#!/usr/bin/env python3
"""Conan test package for the uWSGI logzmq plugin."""

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class UwsgiLogzmqTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        configured = compilers.get("c")
        if configured and os.path.isfile(configured):
            return configured
        if configured:
            found = shutil.which(os.path.basename(configured))
            if found:
                return found
        return os.environ.get("CC") or shutil.which("clang") or "cc"

    def build(self):
        source = os.path.join(self.source_folder, "test_logzmq.c")
        output = os.path.join(self.build_folder, "test_uwsgi_logzmq")
        self.run(f'"{self._compiler()}" "{source}" -o "{output}"')

    def test(self):
        dep = self.dependencies["uwsgi-logzmq"]
        plugin = os.path.join(dep.package_folder, "lib", "uwsgi", "logzmq_plugin.so")
        assert os.path.isfile(plugin), f"missing packaged plugin: {plugin}"
        if not can_run(self):
            self.output.info(
                "Cross-build context: packaged logzmq plugin verified; "
                "runtime probe skipped"
            )
            return
        exe = os.path.join(self.build_folder, "test_uwsgi_logzmq")
        self.run(f'"{exe}" "{plugin}"', env="conanrun")
