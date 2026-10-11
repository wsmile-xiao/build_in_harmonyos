#!/usr/bin/env python3
import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import chdir


class V4lTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["v4l"].cpp_info
        cc = self._compiler_command()
        includes = " ".join(shlex.quote(f"-I{path}") for path in dep.includedirs)
        libdirs = " ".join(shlex.quote(f"-L{path}") for path in dep.libdirs)
        libs = " ".join(f"-l{lib}" for lib in dep.libs + dep.system_libs)
        with chdir(self, self.source_folder):
            self.run(f"{cc} test_v4l.c -o test_v4l {includes} {libdirs} {libs}")

    def test(self):
        if not can_run(self):
            return
        exe = os.path.join(self.source_folder, "test_v4l")
        self.run(exe, env="conanrun")

    def _compiler_command(self):
        compiler_exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler = compiler_exes.get("c") or os.environ.get("CC", "cc")
        if str(self.settings.os) == "OHOS" and self._is_shell_script(compiler):
            shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/bin/sh"
            return "{} {}".format(shlex.quote(shell), shlex.quote(compiler))
        return shlex.quote(compiler)

    @staticmethod
    def _is_shell_script(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(32).startswith(b"#!")
        except OSError:
            return False
