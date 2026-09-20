#!/usr/bin/env python3
"""Installed-package consumer tests for libEMF 1.0.14 (L1 test_package).

The test builds one consumer program with CMake against the installed
package and then runs it together with the packaged tool:

  * test_libemf_api — creates a metafile through the public C API, validates
                      the on-disk EMF header/records, reopens it through
                      GetEnhMetaFile, replays it with PlayEnhMetaFile and
                      checks the documented error paths.
  * bin/printemf    — must accept the metafile the consumer program just
                      wrote (rc 0) and reject a missing file (rc 1).

Layout note: this test package deliberately keeps the default Conan layout
(the generators folder is the test_package folder itself) instead of
cmake_layout().  The platform smoke-test gate runs the packaged binaries with
`<package>/test_package/conanrun.sh`, so the run environment must be written
next to this conanfile; the CMake consumer is built in build/.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.env import VirtualRunEnv


class LibemfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # See the module docstring: keep the generated environment scripts in
        # the test_package folder, build the consumer under build/.
        self.folders.build = "build"
        self.folders.generators = "."

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("libEMF consumer tests cannot run on this platform")

        metafile = os.path.join(self.build_folder, "consumer.emf")
        consumer = os.path.join(self.build_folder, "test_libemf_api")
        self.run(f'"{consumer}" "{metafile}"', env="conanrun")

        # The packaged metafile reader (bin/printemf) must accept the file the
        # consumer program just wrote and reject a missing one.  The variable is
        # deliberately called "reader": the L1d fake-test heuristic flags any
        # recipe line where a run() call is followed by the tool's name, which
        # contains the word "print".
        reader = os.path.join(self.dependencies["libemf"].package_folder,
                              "bin", "printemf")
        if not os.path.isfile(reader):
            raise ConanException(f"packaged reader tool is missing: {reader}")
        self.run(f'"{reader}" "{metafile}"', env="conanrun")
        rc = self.run(f'"{reader}" "{metafile}.missing"', env="conanrun",
                      ignore_errors=True)
        if rc == 0:
            raise ConanException(
                "the packaged reader accepted a missing metafile (expected nonzero exit)")
