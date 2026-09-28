#!/usr/bin/env python3
"""test_package — consumer smoke test for libtypec 0.6.0 on OHOS.

Compiles a C consumer against the packaged libtypec and runs it on target.
The test calls libtypec_init()/libtypec_exit() for real and asserts the
hardware-independent version string; it also proves the OHOS loader accepts
the signed shared object.
"""
import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import chdir


class LibtypecTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libtypec"].cpp_info
        cc = self._compiler_command()
        includes = " ".join(shlex.quote(f"-I{path}") for path in dep.includedirs)
        libdirs = " ".join(shlex.quote(f"-L{path}") for path in dep.libdirs)
        libs = " ".join(f"-l{lib}" for lib in dep.libs + dep.system_libs)
        with chdir(self, self.source_folder):
            # Consumer 1: init/version smoke test.
            self.run(f"{cc} test_libtypec.c -o test_libtypec {includes} {libdirs} {libs}")
            # Consumer 2: query-API surface (graceful no-hardware handling).
            self.run(f"{cc} test_query.c -o test_query {includes} {libdirs} {libs}")

    def test(self):
        if not can_run(self):
            return
        here = self.source_folder
        self.run(os.path.join(here, "test_libtypec"), env="conanrun")
        self.run(os.path.join(here, "test_query"), env="conanrun")

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
