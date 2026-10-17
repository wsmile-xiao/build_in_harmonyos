#!/usr/bin/env python3
"""Conan recipe for ros-genlisp 0.4.18."""

import os
import py_compile
import stat
import xml.etree.ElementTree as ET

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class RosGenlispConan(ConanFile):
    name = "ros-genlisp"
    version = "0.4.18"
    description = "Common Lisp ROS message and service generators"
    license = "BSD-3-Clause"
    homepage = "https://github.com/ros/genlisp"
    url = "https://github.com/ros/genlisp"
    package_type = "unknown"
    settings = "os", "compiler", "build_type", "arch"

    _expected_files = {
        "CMakeLists.txt",
        "package.xml",
        "setup.py",
        "cmake/genlisp-extras.cmake.em",
        "scripts/CMakeLists.txt",
        "scripts/gen_lisp.py",
        "scripts/msg.lisp.template",
        "scripts/srv.lisp.template",
        "src/genlisp/__init__.py",
        "src/genlisp/generate.py",
        "src/genlisp/genlisp_main.py",
    }

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        self._validate_inventory()
        self._validate_package_xml()
        self._compile_python_sources()

    def package(self):
        share_dir = os.path.join(self.package_folder, "share", "ros-genlisp")
        python_dir = os.path.join(self.package_folder, "lib", "python")
        copy(self, "package.xml", src=self.source_folder, dst=share_dir)
        copy(self, "CMakeLists.txt", src=self.source_folder, dst=share_dir)
        copy(self, "setup.py", src=self.source_folder, dst=share_dir)
        copy(self, "*.cmake.em", src=os.path.join(self.source_folder, "cmake"),
             dst=os.path.join(share_dir, "cmake"))
        copy(self, "*.template", src=os.path.join(self.source_folder, "scripts"),
             dst=os.path.join(share_dir, "scripts"))
        copy(self, "CMakeLists.txt", src=os.path.join(self.source_folder, "scripts"),
             dst=os.path.join(share_dir, "scripts"))
        copy(self, "*.py", src=os.path.join(self.source_folder, "src", "genlisp"),
             dst=os.path.join(python_dir, "genlisp"))
        copy(self, "gen_lisp.py", src=os.path.join(self.source_folder, "scripts"),
             dst=os.path.join(self.package_folder, "bin"))

        script = os.path.join(self.package_folder, "bin", "gen_lisp.py")
        if os.path.isfile(script):
            os.chmod(script, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                     stat.S_IRGRP | stat.S_IXGRP |
                     stat.S_IROTH | stat.S_IXOTH)

    def package_info(self):
        share_dir = os.path.join(self.package_folder, "share", "ros-genlisp")
        python_dir = os.path.join(self.package_folder, "lib", "python")
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share/ros-genlisp"]
        self.runenv_info.prepend_path("PYTHONPATH", python_dir)
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.define_path("ROS_GENLISP_DIR", share_dir)

    def package_id(self):
        self.info.clear()

    def _validate_inventory(self):
        missing = [
            relative for relative in sorted(self._expected_files)
            if not os.path.isfile(os.path.join(self.source_folder, relative))
        ]
        if missing:
            raise ConanInvalidConfiguration(f"Missing expected files: {missing}")

    def _validate_package_xml(self):
        package_xml = os.path.join(self.source_folder, "package.xml")
        root = ET.parse(package_xml).getroot()
        name = root.findtext("name")
        version = root.findtext("version")
        if name != "genlisp":
            raise ConanInvalidConfiguration(f"Unexpected package.xml name: {name}")
        if version != self.version:
            raise ConanInvalidConfiguration(f"Unexpected package.xml version: {version}")

    def _compile_python_sources(self):
        python_files = [
            "scripts/gen_lisp.py",
            "src/genlisp/__init__.py",
            "src/genlisp/generate.py",
            "src/genlisp/genlisp_main.py",
        ]
        for relative in python_files:
            py_compile.compile(os.path.join(self.source_folder, relative), doraise=True)
