#!/usr/bin/env python3
"""Conan consumer test for the packaged ROS 1 std_msgs schemas."""

import os
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class RosStdMsgsTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    exports_sources = "test_ros_std_msgs.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_folder = self.dependencies["ros-std-msgs"].package_folder
        test_script = os.path.join(
            self.source_folder,
            "test_ros_std_msgs.py",
        )
        self.run(f'"{sys.executable}" "{test_script}" "{package_folder}"')
