import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.layout import basic_layout


class UnadfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    # Tool-package: a pure CLI test needs no CMake and no build toolchain.
    # VirtualRunEnv alone puts the packaged bin/ on PATH and the packaged
    # lib/ on the link/load path.
    generators = "VirtualRunEnv"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Same shape as the main recipe: the profile keeps
        # tools.build:compiler_executables as a dict, so read it whole.
        ce = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict) or {}
        cc = ce.get("c") or "clang"
        pkg = self.deps_cpp_info["unadf"].package_folder
        # Link against the packaged libadf.a and the packaged headers.
        self.run(
            f"{cc} -std=gnu99 -I{pkg}/include "
            f"{self.source_folder}/test_unadf_lib.c "
            f"-L{pkg}/lib -ladf -o test_unadf_lib"
        )

    def test(self):
        if not can_run(self):
            return
        vr = VirtualRunEnv(self)
        vr.generate()
        env = vr.vars
        env.save()
        self.run("bash test_unadf_cli.sh", env="conanrun")
