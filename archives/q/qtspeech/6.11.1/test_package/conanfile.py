#!/usr/bin/env python3
"""Consumer test for Qt Speech 6.11.1 using its mock engine."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class QtSpeechTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        qtbase = self.dependencies["qtbase"].package_folder
        qtmultimedia = self.dependencies["qtmultimedia"].package_folder
        qtspeech = self.dependencies["qtspeech"].package_folder
        tc.cache_variables.update(
            {
                "Qt6_DIR": os.path.join(qtbase, "lib", "cmake", "Qt6"),
                "Qt6Multimedia_DIR": os.path.join(
                    qtmultimedia, "lib", "cmake", "Qt6Multimedia"
                ),
                "Qt6TextToSpeech_DIR": os.path.join(
                    qtspeech, "lib", "cmake", "Qt6TextToSpeech"
                ),
                "CMAKE_MODULE_PATH": os.path.join(
                    qtbase, "lib", "cmake", "Qt6", "platforms"
                ),
            }
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanInvalidConfiguration("qtspeech test package has no build bindir")
        qtspeech = self.dependencies["qtspeech"].package_folder
        test_env = Environment()
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_env.prepend_path("QT_PLUGIN_PATH", os.path.join(qtspeech, "plugins"))
        with test_env.vars(self).apply():
            self.run(
                os.path.join(bindirs[0], "test_qtspeech"),
                env="conanrun",
                ignore_errors=False,
            )
