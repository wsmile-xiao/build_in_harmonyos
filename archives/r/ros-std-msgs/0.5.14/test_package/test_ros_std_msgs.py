#!/usr/bin/env python3
"""Validate the public schemas from a packaged ros-std-msgs archive."""

import pathlib
import re
import sys
import xml.etree.ElementTree as element_tree


EXPECTED_FIELDS = {
    "Bool.msg": [("bool", "data")],
    "Byte.msg": [("byte", "data")],
    "ByteMultiArray.msg": [
        ("MultiArrayLayout", "layout"),
        ("byte[]", "data"),
    ],
    "Char.msg": [("char", "data")],
    "ColorRGBA.msg": [
        ("float32", "r"),
        ("float32", "g"),
        ("float32", "b"),
        ("float32", "a"),
    ],
    "Duration.msg": [("duration", "data")],
    "Empty.msg": [],
    "Float32.msg": [("float32", "data")],
    "Float32MultiArray.msg": [
        ("MultiArrayLayout", "layout"),
        ("float32[]", "data"),
    ],
    "Float64.msg": [("float64", "data")],
    "Float64MultiArray.msg": [
        ("MultiArrayLayout", "layout"),
        ("float64[]", "data"),
    ],
    "Header.msg": [
        ("uint32", "seq"),
        ("time", "stamp"),
        ("string", "frame_id"),
    ],
    "Int16.msg": [("int16", "data")],
    "Int16MultiArray.msg": [
        ("MultiArrayLayout", "layout"),
        ("int16[]", "data"),
    ],
    "Int32.msg": [("int32", "data")],
    "Int32MultiArray.msg": [
        ("MultiArrayLayout", "layout"),
        ("int32[]", "data"),
    ],
    "Int64.msg": [("int64", "data")],
    "Int64MultiArray.msg": [
        ("MultiArrayLayout", "layout"),
        ("int64[]", "data"),
    ],
    "Int8.msg": [("int8", "data")],
    "Int8MultiArray.msg": [
        ("MultiArrayLayout", "layout"),
        ("int8[]", "data"),
    ],
    "MultiArrayDimension.msg": [
        ("string", "label"),
        ("uint32", "size"),
        ("uint32", "stride"),
    ],
    "MultiArrayLayout.msg": [
        ("MultiArrayDimension[]", "dim"),
        ("uint32", "data_offset"),
    ],
    "String.msg": [("string", "data")],
    "Time.msg": [("time", "data")],
    "UInt16.msg": [("uint16", "data")],
    "UInt16MultiArray.msg": [
        ("MultiArrayLayout", "layout"),
        ("uint16[]", "data"),
    ],
    "UInt32.msg": [("uint32", "data")],
    "UInt32MultiArray.msg": [
        ("MultiArrayLayout", "layout"),
        ("uint32[]", "data"),
    ],
    "UInt64.msg": [("uint64", "data")],
    "UInt64MultiArray.msg": [
        ("MultiArrayLayout", "layout"),
        ("uint64[]", "data"),
    ],
    "UInt8.msg": [("uint8", "data")],
    "UInt8MultiArray.msg": [
        ("MultiArrayLayout", "layout"),
        ("uint8[]", "data"),
    ],
}
EXPECTED_MESSAGES = set(EXPECTED_FIELDS)
BUILTIN_TYPES = {
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
FIELD_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
check_count = 0


def check(condition, message):
    global check_count
    check_count += 1
    if not condition:
        raise RuntimeError(message)


def parse_message(path, declared_messages):
    fields = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        1,
    ):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2:
            raise RuntimeError(
                f"{path.name}:{line_number}: invalid field declaration"
            )
        field_type, field_name = parts
        base_type = re.sub(r"\[[0-9]*\]$", "", field_type)
        if base_type not in BUILTIN_TYPES and base_type not in declared_messages:
            raise RuntimeError(
                f"{path.name}:{line_number}: unresolved type {field_type}"
            )
        if not FIELD_PATTERN.fullmatch(field_name):
            raise RuntimeError(
                f"{path.name}:{line_number}: invalid field name {field_name}"
            )
        fields.append((field_type, field_name))
    return fields


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: test_ros_std_msgs.py <package-folder>")

    package_folder = pathlib.Path(sys.argv[1]).resolve()
    message_folder = package_folder / "share" / "ros-std-msgs" / "msg"
    actual_messages = {path.name for path in message_folder.glob("*.msg")}
    check(
        actual_messages == EXPECTED_MESSAGES,
        "The packaged message inventory does not match std_msgs 0.5.14",
    )

    declared_messages = {
        pathlib.Path(filename).stem for filename in actual_messages
    }
    for filename in sorted(EXPECTED_MESSAGES):
        fields = parse_message(message_folder / filename, declared_messages)
        check(
            fields == EXPECTED_FIELDS[filename],
            f"Unexpected public schema in {filename}: {fields}",
        )

    package_xml = element_tree.parse(
        package_folder / "share" / "ros-std-msgs" / "package.xml"
    ).getroot()
    check(package_xml.findtext("name") == "std_msgs", "Wrong ROS package name")
    check(package_xml.findtext("version") == "0.5.14", "Wrong ROS package version")

    if check_count != 35:
        raise RuntimeError(f"Expected 35 checks, executed {check_count}")
    print("ros-std-msgs package checks passed: 35/35")


if __name__ == "__main__":
    main()
