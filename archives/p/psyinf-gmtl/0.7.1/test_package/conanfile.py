#!/usr/bin/env python3
"""test_package for psyinf-gmtl — Conan L1 consumer test.

This is the rule12 consumer end-to-end layer: ``consumer.cpp`` is a real
consumer translation unit that drives the public GMTL API through a complete
multi-stage geometric workflow (transform pipeline, quaternion cross-check,
ray/sphere and ray/plane intersection, AABB fitting, quaternion/matrix round
trip, math helpers) and asserts the numeric result of every stage.

Because the package is cross-compiled for OHOS, the binary is executed through
the profile's ``CMAKE_CROSSCOMPILING_EMULATOR`` (the same qemu wrapper the
recipe uses for the upstream CppUnit suite) rather than on the build host.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class GmtlTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        exe = os.path.join(self.cpp.build.bindirs[0], "consumer")

        if can_run(self):
            self.run(f'"{exe}"', env="conanrun")
            return

        # Cross-built: run the OHOS binary through the profile's emulator.
        extra = self.conf.get(
            "tools.cmake.cmaketoolchain:extra_variables", check_type=dict
        ) or {}
        emulator = extra.get("CMAKE_CROSSCOMPILING_EMULATOR")
        if not emulator:
            # Reporting success here would mean the 25 consumer assertions --
            # the only OHOS end-to-end coverage this package has -- never ran.
            # A zero-assertion "pass" is worse than a failure, so refuse it.
            raise ConanException(
                "cross-building without CMAKE_CROSSCOMPILING_EMULATOR: the "
                "consumer end-to-end binary was linked but cannot be executed, "
                "so no test result can be claimed (use ohos-aarch64-run)"
            )

        self.output.info("Running consumer e2e under the OHOS emulator")
        # Validate the emulator rather than interpolating an unchecked conf
        # value into a shell command line.
        if not (os.path.isabs(emulator) and os.path.isfile(emulator)):
            raise ConanException(
                "CMAKE_CROSSCOMPILING_EMULATOR is not an existing absolute "
                "path: %r" % (emulator,)
            )
        # The emulator is invoked directly -- no shell is involved, so the
        # path needs no quoting beyond the argv quoting Conan already applies.
        self.run(f'"{emulator}" "{exe}"')
