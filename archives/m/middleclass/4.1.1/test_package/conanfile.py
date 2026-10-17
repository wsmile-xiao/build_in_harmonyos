#!/usr/bin/env python3
"""Conan test_package for middleclass — verifies the Lua module loads and works.

This test uses the lua interpreter from the lua/5.4.8.1 dependency
(made available on PATH via VirtualRunEnv) to run a Lua test script
that requires middleclass and exercises its OOP API.
"""
import os

from conan import ConanFile


class MiddleclassTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # lua is on PATH via lua/5.4.8.1 runenv_info (prepend PATH)
        # LUA_PATH is set by middleclass package_info runenv_info
        test_script = os.path.join(self.source_folder, "test.lua")
        self.run(f'lua "{test_script}"', env="conanrun")
