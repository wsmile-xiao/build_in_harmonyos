#!/usr/bin/env python3
"""Conan test_package for nanomsgxx/0.2.

R34: test_nanomsgxx.cpp really calls the packaged library — creates nnxx
sockets (nnxx::SP/nnxx::PAIR), binds/connects over inproc:// and round-trips
a message — and the resulting binary is executed on the target (not a
print-only shell).  CI runs this automatically via `conan create`.

The compile step gathers include/lib paths from the whole dependency graph
(nanomsgxx + its transitive nanomsg dependency) because the nnxx headers
themselves include <nanomsg/...> headers.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class NanomsgxxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("Skip test: cannot run the target binary on this host")
            return

        # Gather include/lib dirs + libs from the full dependency graph
        # (nanomsgxx and its transitive nanomsg dependency).
        include_dirs = []
        lib_dirs = []
        libs = []
        for _, dep in self.dependencies.items():
            info = dep.cpp_info
            if info.includedir:
                include_dirs.append(info.includedir)
            if info.libdir:
                lib_dirs.append(info.libdir)
            libs.extend(info.libs or [])
        # Link order: libnnxx links against libnanomsg.
        link_libs = [f"-l{lib}" for lib in libs]

        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cxx = compilers.get("cpp") or "clang++"

        src = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "test_nanomsgxx.cpp")
        exe = os.path.join(self.build_folder, "test_nanomsgxx")

        includes = " ".join(f"-I'{d}'" for d in include_dirs)
        lib_paths = " ".join(f"-L'{d}'" for d in lib_dirs)

        self.run(
            f"{cxx} '{src}' {includes} {lib_paths} {' '.join(link_libs)} "
            f"-pthread -o '{exe}'",
            env="conanrun",
        )
        # Shared libs must be resolvable at runtime (libnnxx + libnanomsg).
        with VirtualRunEnv(self).vars().apply():
            self.run(f"'{exe}'", env="conanrun")
