#!/usr/bin/env python3
"""Consumer tests for iir1 1.10.0."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class Iir1TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning(
                "Cross build: consumer linked successfully but cannot run "
                "on the build host."
            )
            return

        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executable = os.path.join(
            self.cpp.build.bindirs[0], "iir1_consumer" + suffix
        )
        cases = (
            "butterworth-lowpass-2",
            "butterworth-lowpass-4",
            "butterworth-highpass-2",
            "butterworth-highpass-4",
            "butterworth-bandpass-2",
            "butterworth-bandpass-4",
            "butterworth-bandstop-2",
            "butterworth-bandstop-4",
            "butterworth-lowshelf-2",
            "butterworth-lowshelf-4",
            "butterworth-highshelf-2",
            "butterworth-highshelf-4",
            "butterworth-bandshelf-2",
            "butterworth-bandshelf-4",
            "chebyshev1-lowpass-2",
            "chebyshev1-lowpass-4",
            "chebyshev1-highpass-2",
            "chebyshev1-highpass-4",
            "chebyshev1-bandpass-2",
            "chebyshev1-bandpass-4",
            "chebyshev1-bandstop-2",
            "chebyshev1-bandstop-4",
            "chebyshev1-lowshelf-2",
            "chebyshev1-lowshelf-4",
            "chebyshev1-highshelf-2",
            "chebyshev1-highshelf-4",
            "chebyshev1-bandshelf-2",
            "chebyshev1-bandshelf-4",
            "chebyshev2-lowpass-2",
            "chebyshev2-highpass-2",
            "chebyshev2-bandpass-2",
            "chebyshev2-bandstop-2",
            "chebyshev2-lowshelf-2",
            "chebyshev2-highshelf-2",
            "chebyshev2-bandshelf-2",
            "rbj-lowpass",
            "rbj-highpass",
            "rbj-bandpass1",
            "rbj-bandpass2",
            "rbj-bandstop",
            "rbj-notch",
            "rbj-lowshelf",
            "rbj-highshelf",
            "rbj-bandshelf",
            "rbj-allpass",
            "invalid-parameters",
        )
        failures = []
        for case in cases:
            try:
                self.run(
                    f'"{executable}" {case}',
                    env="conanrun",
                    cwd=self.build_folder,
                )
            except ConanException as error:
                failures.append(f"{case}: {error}")

        if failures:
            details = "\n".join(f"- {failure}" for failure in failures)
            raise ConanException(
                f"{len(failures)} of {len(cases)} consumer cases failed:\n"
                f"{details}"
            )
