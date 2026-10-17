#!/usr/bin/env python3
"""Conan test_package for ismrmrd 1.15.0 — consumer-view verification.

Simulates a downstream HarmonyOS PC application that consumes the installed
ismrmrd package through its *public* interface only:

  * ``test_consumer`` — the public C API (flags, channel masks, acquisition and
    ndarray lifecycle) compiled and linked through CMakeDeps.
  * ``test_ohos`` — the public C++ XML interchange API: build an
    ``IsmrmrdHeader`` through the struct API, serialise it, deserialise it back
    and compare. Exercised for the OHOS target specifically.

Both binaries are built in ``build()`` and executed in ``test()`` so a
compile/link/runtime failure in a real consumer is surfaced by ``conan create``.

``VirtualRunEnv`` is declared explicitly on purpose: giving ``generators``
*replaces* Conan's default generator set, so omitting it means there is no
``conanrun`` environment and the consumers fail at load time with
``Error loading shared library ...`` once ``libismrmrd.so`` carries a SONAME
and therefore has to be located through ``LD_LIBRARY_PATH`` together with its
transitive dependencies (hdf5, libaec, ...).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class IsmrmrdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.generate()

        # Make the dependency config packages reachable regardless of the
        # layout CMakeDeps chose for them.
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.extend(
                    [
                        f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")',
                        f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")',
                        f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")',
                    ]
                )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # ctest spawns the consumer binaries, so it must run under the
        # conanrun environment too (not just the direct self.run calls below).
        self.run(
            'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                self.build_folder
            ),
            env="conanrun",
        )
        for binary in ("test_consumer", "test_ohos"):
            self.run(
                os.path.join(self.cpp.build.bindirs[0], binary),
                env="conanrun",
            )
