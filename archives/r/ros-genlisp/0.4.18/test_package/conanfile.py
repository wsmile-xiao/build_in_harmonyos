#!/usr/bin/env python3
"""Conan consumer test for ros-genlisp 0.4.18."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class RosGenlispTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    exports_sources = "test_ros_genlisp.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_folder = self.dependencies["ros-genlisp"].package_folder
        expected = [
            os.path.join(package_folder, "share", "ros-genlisp", "package.xml"),
            os.path.join(package_folder, "share", "ros-genlisp", "cmake", "genlisp-extras.cmake.em"),
            os.path.join(package_folder, "share", "ros-genlisp", "scripts", "msg.lisp.template"),
            os.path.join(package_folder, "share", "ros-genlisp", "scripts", "srv.lisp.template"),
            os.path.join(package_folder, "lib", "python", "genlisp", "generate.py"),
            os.path.join(package_folder, "bin", "gen_lisp.py"),
        ]
        missing = [path for path in expected if not os.path.isfile(path)]
        if missing:
            raise AssertionError(f"Missing ros-genlisp files: {missing}")

        if not can_run(self):
            self.output.info("Cross-building: verified package layout only.")
            return

        script = os.path.join(self.source_folder, "test_ros_genlisp.py")
        self.run(f'"{sys.executable}" "{script}" "{package_folder}"', env="conanrun")
