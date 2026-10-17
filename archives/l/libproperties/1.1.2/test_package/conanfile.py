#!/usr/bin/env python3
"""Conan test_package for libproperties 1.1.2 (layer-2 consumer verification).

CI gate notes (ci/conan/build_and_test.sh):
  * L0d requires ``test()`` to invoke the produced binaries directly — the CMake
    helper entry point is reported as ``stub_test_method`` by that gate.
  * L1d rejects runner lines that only shell out to trivial no-op commands;
    here the two binaries do all the work themselves.
  * Bare command names are not PATH-searched by the OHOS spawn path, so the
    absolute build-folder path is resolved before spawning.
  * The package must declare ``layout()`` or binaries land in the source folder.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class LibpropertiesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Layer 2: public API consumer (compiles against the installed header and
        # links the installed library).
        self.run('"{}"'.format(self._binary("test_libproperties_api")), env="conanrun")

        # HarmonyOS-specific guard: only meaningful for the default shared build;
        # a static build ships no .so at all, so say so instead of passing quietly.
        if self._packaged_library_is_shared():
            self.run('"{}"'.format(self._binary("test_libproperties_soname")), env="conanrun")
        else:
            self.output.info(
                "static build (shared=False): DT_SONAME guard does not apply"
            )

    def _binary(self, name):
        """Absolute path of a binary produced by this test_package's build()."""
        candidates = [
            os.path.join(self.build_folder, name),
            os.path.join(self.build_folder, str(self.settings.build_type), name),
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate
        raise ConanException(
            "test_package binary {!r} not found; looked in: {}".format(
                name, ", ".join(candidates)
            )
        )

    def _packaged_library_is_shared(self):
        lib_dir = os.path.join(self.dependencies["libproperties"].package_folder, "lib")
        if not os.path.isdir(lib_dir):
            return False
        return any(
            entry.endswith(".so") or ".so." in entry
            for entry in os.listdir(lib_dir)
        )
