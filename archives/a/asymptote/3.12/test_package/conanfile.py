#!/usr/bin/env python3
"""Conan test_package for asymptote 3.12.

R34: the test must exercise the packaged binary for real.  We build a small
C harness that (1) runs `asy --version` and requires "Asymptote version 3.12"
in the output, and (2) renders a trivial unlabeled .asy scene to EPS and
requires the output file to exist and be non-empty (no LaTeX involved).
The gsl shared library (dependency of asy) and the packaged share/ tree
(base modules) are exported through LD_LIBRARY_PATH / ASYMPTOTE_SYSDIR env
vars so the harness can find them.  cpp_info.libdirs may be relative ("lib"),
so they are joined with package_folder to build absolute search paths.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class AsymptoteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # bring gsl (shared dep of asy) into the direct graph so its
        # package_folder is resolvable for LD_LIBRARY_PATH
        self.requires("gsl/2.8")

    def build(self):
        source = os.path.join(self.source_folder, "test_package.c")
        executable = os.path.join(self.build_folder, "test_package")
        compiler = os.environ.get("CC", "cc")
        self.run(f'{compiler} "{source}" -o "{executable}"')

    def test(self):
        if can_run(self):
            executable = os.path.join(self.build_folder, "test_package")
            asym = self.dependencies["asymptote"]
            env = Environment()
            # locate the packaged asy binary
            env.prepend_path("PATH", os.path.join(asym.package_folder, "bin"))
            # asy links against shared libgsl/libgslcblas; make them findable
            for dep in self.dependencies.values():
                if dep.package_folder is None:
                    continue
                for libdir in dep.cpp_info.libdirs:
                    abs_libdir = libdir if os.path.isabs(libdir) else \
                        os.path.join(dep.package_folder, libdir)
                    env.prepend_path("LD_LIBRARY_PATH", abs_libdir)
            # point asy at the packaged base modules (share/asymptote)
            env.define("ASYMPTOTE_SYSDIR",
                       os.path.join(asym.package_folder, "share", "asymptote"))
            # full path to the packaged binary (PATH-independent)
            env.define("ASYMPTOTE_BIN",
                       os.path.join(asym.package_folder, "bin", "asy"))
            with env.vars(self).apply():
                # env="conanrun" also puts the package bin/ on PATH
                self.run(f'"{executable}"', env="conanrun")
