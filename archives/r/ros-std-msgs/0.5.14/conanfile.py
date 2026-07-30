#!/usr/bin/env python3
"""Conan recipe for the ROS 1 std_msgs 0.5.14 data package."""

import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class RosStdMsgsConan(ConanFile):
    name = "ros-std-msgs"
    version = "0.5.14"
    description = "Standard ROS 1 message definitions"
    license = "BSD-3-Clause"
    homepage = "https://github.com/ros/std_msgs"
    url = "https://github.com/ros/std_msgs"
    package_type = "unknown"
    settings = "os", "compiler", "build_type", "arch"

    _expected_messages = {
        "Bool.msg",
        "Byte.msg",
        "ByteMultiArray.msg",
        "Char.msg",
        "ColorRGBA.msg",
        "Duration.msg",
        "Empty.msg",
        "Float32.msg",
        "Float32MultiArray.msg",
        "Float64.msg",
        "Float64MultiArray.msg",
        "Header.msg",
        "Int16.msg",
        "Int16MultiArray.msg",
        "Int32.msg",
        "Int32MultiArray.msg",
        "Int64.msg",
        "Int64MultiArray.msg",
        "Int8.msg",
        "Int8MultiArray.msg",
        "MultiArrayDimension.msg",
        "MultiArrayLayout.msg",
        "String.msg",
        "Time.msg",
        "UInt16.msg",
        "UInt16MultiArray.msg",
        "UInt32.msg",
        "UInt32MultiArray.msg",
        "UInt64.msg",
        "UInt64MultiArray.msg",
        "UInt8.msg",
        "UInt8MultiArray.msg",
    }
    _builtin_types = {
        "bool",
        "byte",
        "char",
        "duration",
        "float32",
        "float64",
        "int8",
        "int16",
        "int32",
        "int64",
        "string",
        "time",
        "uint8",
        "uint16",
        "uint32",
        "uint64",
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self._validate_message_definitions()

    def package(self):
        copy(
            self,
            "*.msg",
            src=os.path.join(self.source_folder, "msg"),
            dst=os.path.join(
                self.package_folder,
                "share",
                "ros-std-msgs",
                "msg",
            ),
        )
        copy(
            self,
            "package.xml",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "ros-std-msgs"),
        )
        copy(
            self,
            "CMakeLists.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "ros-std-msgs"),
        )
        copy(
            self,
            "CHANGELOG.rst",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "ros-std-msgs"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share/ros-std-msgs"]
        self.runenv_info.define_path(
            "ROS_STD_MSGS_DIR",
            os.path.join(self.package_folder, "share", "ros-std-msgs"),
        )

    def package_id(self):
        self.info.clear()

    def _validate_message_definitions(self):
        message_folder = os.path.join(self.source_folder, "msg")
        actual = {
            filename
            for filename in os.listdir(message_folder)
            if filename.endswith(".msg")
        }
        if actual != self._expected_messages:
            missing = sorted(self._expected_messages - actual)
            extra = sorted(actual - self._expected_messages)
            raise ConanInvalidConfiguration(
                f"Unexpected std_msgs inventory; missing={missing}, extra={extra}"
            )

        declared_messages = {
            os.path.splitext(filename)[0] for filename in actual
        }
        field_pattern = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
        for filename in sorted(actual):
            path = os.path.join(message_folder, filename)
            with open(path, encoding="utf-8") as message_file:
                for line_number, raw_line in enumerate(message_file, 1):
                    line = raw_line.split("#", 1)[0].strip()
                    if not line:
                        continue
                    parts = line.split()
                    if len(parts) != 2:
                        raise ConanInvalidConfiguration(
                            f"{filename}:{line_number}: invalid field declaration"
                        )
                    field_type, field_name = parts
                    base_type = re.sub(r"\[[0-9]*\]$", "", field_type)
                    if (
                        base_type not in self._builtin_types
                        and base_type not in declared_messages
                    ):
                        raise ConanInvalidConfiguration(
                            f"{filename}:{line_number}: unresolved type {field_type}"
                        )
                    if not field_pattern.fullmatch(field_name):
                        raise ConanInvalidConfiguration(
                            f"{filename}:{line_number}: invalid field name {field_name}"
                        )
