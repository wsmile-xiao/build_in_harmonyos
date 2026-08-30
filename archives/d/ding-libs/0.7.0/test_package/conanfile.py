#!/usr/bin/env python3
"""Consumer test for the public ding-libs APIs."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class DingLibsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _absolute(root, path):
        return path if os.path.isabs(path) else os.path.join(root, path)

    def _compiler(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        configured = compiler_executables.get("c") if compiler_executables else None
        if configured:
            configured = str(configured).split()[0].strip("\"'")
            if os.path.isfile(configured):
                return configured
        compiler = shutil.which("clang") or shutil.which("cc")
        if not compiler:
            raise RuntimeError("cannot find a C compiler")
        return compiler

    def build(self):
        dependency = self.dependencies["ding-libs"]
        package_root = dependency.package_folder
        include_dirs = [
            self._absolute(package_root, path)
            for path in (dependency.cpp_info.includedirs or ["include"])
        ]
        lib_dirs = [
            self._absolute(package_root, path)
            for path in (dependency.cpp_info.libdirs or ["lib"])
        ]

        include_flags = " ".join("-I" + shlex.quote(path) for path in include_dirs)
        library_flags = " ".join("-L" + shlex.quote(path) for path in lib_dirs)
        rpath_flags = " ".join(
            "-Wl,-rpath," + shlex.quote(path) for path in lib_dirs
        )
        # Exercise both public libraries, rather than only checking that a
        # header can be included.
        command = (
            f"{shlex.quote(self._compiler())} -std=gnu11 -Wall -Wextra "
            f"{include_flags} test.c -o ding-libs-test "
            f"{library_flags} {rpath_flags} -lini_config -ldhash -lm -lpthread"
        )
        self.run(command, env="conanbuild")

    def test(self):
        if can_run(self):
            self.run("./ding-libs-test", env="conanrun")
        else:
            self.output.info("cross-building: compile/link test completed")
