#!/usr/bin/env python3
"""Conan test_package — triangle 1.6.

Two independent checks, both against the packaged artefacts:

1. ``test_triangle`` compiles against ``libtriangle.a`` + ``triangle.h`` and
   drives the real embeddable API (``triangulate`` / ``trifree``) on the unit
   square — see src/test_triangle.c.
2. the packaged ``bin/triangle`` CLI is run on a PSLG written here, and its
   ``.1.node`` / ``.1.ele`` / ``.1.poly`` outputs are required to exist.  That
   is what proves the exact-arithmetic code path executes on the target, not
   merely that it linked.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout

PSLG = """4 2 0 0
1 0.0 0.0
2 1.0 0.0
3 1.0 1.0
4 0.0 1.0
4 0
1 1 2
2 2 3
3 3 4
4 4 1
0
"""


class TriangleTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 1. embeddable API consumer
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_triangle")
        self.run(test_bin, env="conanrun")

        # 2. CLI smoke run on a PSLG generated here.
        #    Use the packaged binary by absolute path: triangle is a
        #    static-library package, so its bin/ is not added to the build
        #    environment the way an application package's bin/ would be, and
        #    the generated conanrun environment for a library carries no PATH.
        dependency = self.dependencies[self.tested_reference_str]
        cli = os.path.join(dependency.package_folder,
                           dependency.cpp_info.bindirs[0], "triangle")
        workdir = self.build_folder
        with open(os.path.join(workdir, "test_square.poly"), "w") as handle:
            handle.write(PSLG)
        self.run('"{}" -pzQ test_square.poly'.format(cli), cwd=workdir)
        for suffix in (".1.node", ".1.ele", ".1.poly"):
            produced = os.path.join(workdir, "test_square" + suffix)
            if not os.path.isfile(produced):
                raise ConanException(
                    "triangle CLI did not produce test_square{}".format(suffix))
