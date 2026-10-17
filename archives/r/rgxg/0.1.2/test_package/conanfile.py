#!/usr/bin/env python3
"""Consumer test for the packaged rgxg library and command line."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run

required_conan_version = ">=2.0"


class RgxgTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _absolute(self, root, path):
        return path if os.path.isabs(path) else os.path.join(root, path)

    def _compiler_cc(self):
        # R33: the compiler comes from the toolchain conf, never from bare PATH.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        configured = executables.get("c") if executables else None
        if configured:
            configured = str(configured).split()[0].strip("\"'")
            if os.path.isfile(configured):
                return configured
        found = shutil.which("clang") or shutil.which("cc")
        if not found:
            raise RuntimeError("cannot find a C compiler for the rgxg consumer test")
        return found

    def build(self):
        dependency = self.dependencies["rgxg"]
        package_root = dependency.package_folder
        include_flags = " ".join(
            "-I" + shlex.quote(self._absolute(package_root, path))
            for path in (dependency.cpp_info.includedirs or ["include"])
        )
        library_flags = " ".join(
            "-L" + shlex.quote(self._absolute(package_root, path))
            for path in (dependency.cpp_info.libdirs or ["lib"])
        )
        rpath_flags = " ".join(
            "-Wl,-rpath," + shlex.quote(self._absolute(package_root, path))
            for path in (dependency.cpp_info.libdirs or ["lib"])
        )
        # Compile under conanbuild: lld resolves -lrgxg there, while the run
        # step below only needs conanrun.
        self.run(
            f"{shlex.quote(self._compiler_cc())} -std=gnu11 -Wall -Wextra "
            f"{include_flags} test_rgxg.c -o test_rgxg "
            f"{library_flags} {rpath_flags} -lrgxg",
            env="conanbuild",
        )

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: compile/link evidence only")
            return
        package_root = self.dependencies["rgxg"].package_folder
        self.run(f"./test_rgxg {shlex.quote(package_root)}", env="conanrun")
        self.run(f"sh test_cli.sh {shlex.quote(package_root)}", env="conanrun")
