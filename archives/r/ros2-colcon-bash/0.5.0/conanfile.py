#!/usr/bin/env python3
"""Conan recipe for ros2-colcon-bash 0.5.0.

This is a pure Python colcon shell extension. It is installed into an isolated
site-packages directory with minimal package metadata and entry points, without
compiling native code.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, save
from conan.tools.layout import basic_layout


class Ros2ColconBashConan(ConanFile):
    name = "ros2-colcon-bash"
    version = "0.5.0"
    description = "Bash shell extension for colcon"
    license = "Apache-2.0"
    homepage = "https://github.com/colcon/colcon-bash"
    url = ""

    settings = "os", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        pass

    def package(self):
        site_packages = os.path.join(self.package_folder, "lib", "python3", "site-packages")
        copy(self, "*", os.path.join(self.source_folder, "colcon_bash"),
             os.path.join(site_packages, "colcon_bash"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "share", "ros2-colcon-bash"))
        copy(self, "README.rst", self.source_folder, os.path.join(self.package_folder, "share", "ros2-colcon-bash"))
        copy(self, "setup.cfg", self.source_folder, os.path.join(self.package_folder, "share", "ros2-colcon-bash"))
        copy(self, "*", os.path.join(self.source_folder, "test"),
             os.path.join(self.package_folder, "share", "ros2-colcon-bash", "test"))

        dist_info = os.path.join(site_packages, "colcon_bash-0.5.0.dist-info")
        metadata = """Metadata-Version: 2.1
Name: colcon-bash
Version: 0.5.0
Summary: Extension for colcon to provide Bash scripts.
Home-page: https://github.com/colcon/colcon-bash
License: Apache License, Version 2.0
Requires-Dist: colcon-core >=0.12.0
"""
        entry_points = """[colcon_core.shell]
bash = colcon_bash.shell.bash:BashShell
"""
        wheel = """Wheel-Version: 1.0
Generator: conan
Root-Is-Purelib: true
Tag: py3-none-any
"""
        save(self, os.path.join(dist_info, "METADATA"), metadata)
        save(self, os.path.join(dist_info, "entry_points.txt"), entry_points)
        save(self, os.path.join(dist_info, "WHEEL"), wheel)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        site_packages = os.path.join(self.package_folder, "lib", "python3", "site-packages")
        self.runenv_info.append_path("PYTHONPATH", site_packages)
        self.buildenv_info.append_path("PYTHONPATH", site_packages)
