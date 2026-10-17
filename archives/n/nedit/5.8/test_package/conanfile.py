#!/usr/bin/env python3
"""Conan test_package for nedit 5.8 (HarmonyOS PC / aarch64).

Drives ``test_nedit.py`` against the installed package by absolute path: the
binaries are executed from the package cache, never through a ``PATH`` lookup,
so the test genuinely depends on the packaged artifacts (and on their dynamic
dependency ``libXm.so.4`` being loadable from the Conan graph).
"""

import os
import sys

from conan import ConanFile
from conan.tools.build import cross_building


class NeditTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only the package presence is checked")
            return

        dependency = self.dependencies["nedit"]
        bin_dir = os.path.join(dependency.package_folder, "bin")
        app_defaults = os.path.join(
            dependency.package_folder, "share", "X11", "app-defaults", "NEdit")
        script = os.path.join(self.recipe_folder, "test_nedit.py")

        # nedit links libXm.so.4, which links libXt/libXext/libX11/libSM/libICE.
        # conanrun only carries the runenv of the nodes that declare one, so the
        # libdirs of *every* node of the graph are prepended explicitly, exactly
        # as the ncdc and openvi packages do for their dynamic executables.
        libdirs = []
        for node in self.dependencies.values():
            folder = getattr(node, "package_folder", None)
            if not folder:
                continue
            for libdir in node.cpp_info.aggregated_components().libdirs:
                libdirs.append(libdir if os.path.isabs(libdir)
                               else os.path.join(folder, libdir))
        prefix = ""
        if libdirs:
            joined = ":".join(dict.fromkeys(libdirs)).replace("\\", "/")
            prefix = 'LD_LIBRARY_PATH="{}:$LD_LIBRARY_PATH" '.format(joined)

        self.run(
            f'{prefix}"{sys.executable}" "{script}" "{bin_dir}" "{app_defaults}"',
            env="conanrun",
        )
