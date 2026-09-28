#!/usr/bin/env python3
"""Consumer tests for mts-esp."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MtsEspTestConan(ConanFile):
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
        test_binary = os.path.join(
            self.cpp.build.bindirs[0], "test_mts_esp"
        )
        for test_case in (
            "client_registration",
            "default_frequency",
            "retuning_identity",
            "frequency_to_note",
            "default_scale",
            "note_filter",
            "sysex_single_note",
            "master_offline_safety",
        ):
            self.run(
                f'"{test_binary}" "{test_case}"',
                env="conanrun",
            )

        provider_dir = self.cpp.build.libdirs[0]
        self.run(
            f'LD_LIBRARY_PATH="{provider_dir}'
            '${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" '
            f'"{test_binary}" "ohos_dynamic_provider"',
            env="conanrun",
        )
