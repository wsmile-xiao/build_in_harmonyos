#!/usr/bin/env python3
"""Consumer test for adept-math."""

import os
import shlex
import subprocess

from conan import ConanFile
from conan.tools.build import can_run


class AdeptMathTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["adept-math"]
        cpp_info = dep.cpp_info.aggregated_components()
        cxx = self._cxx()
        exe = os.path.join(self.build_folder, self._exe_name("test_adept_math"))
        source = os.path.join(self.source_folder, "test.cpp")

        include_flags = " ".join(f"-I{self._q(path)}" for path in cpp_info.includedirs)
        libdir_flags = " ".join(f"-L{self._q(path)}" for path in cpp_info.libdirs)
        lib_flags = " ".join(f"-l{lib}" for lib in (cpp_info.libs + cpp_info.system_libs))
        flags = self._build_type_flags() + ["-std=c++11"]

        cmd = (
            f"{self._q(cxx)} {' '.join(flags)} {include_flags} "
            f"{self._q(source)} {libdir_flags} {lib_flags} -o {self._q(exe)}"
        )
        self.run(cmd)

    def test(self):
        if not can_run(self):
            self.output.info("consumer compiled; target execution is unavailable")
            return
        exe = os.path.join(self.build_folder, self._exe_name("test_adept_math"))
        self.run(self._q(exe), env="conanrun")

    def _cxx(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get("cpp") or compilers.get("cxx") or "c++"

    def _build_type_flags(self):
        build_type = str(self.settings.build_type)
        if build_type == "Debug":
            return ["-O0", "-g"]
        if build_type == "RelWithDebInfo":
            return ["-O2", "-g", "-DNDEBUG"]
        if build_type == "MinSizeRel":
            return ["-Os", "-DNDEBUG"]
        return ["-O2", "-DNDEBUG"]

    def _exe_name(self, name):
        return name + (".exe" if str(self.settings.os) == "Windows" else "")

    def _q(self, value):
        value = str(value)
        if os.name == "nt":
            return subprocess.list2cmdline([value])
        return shlex.quote(value)
