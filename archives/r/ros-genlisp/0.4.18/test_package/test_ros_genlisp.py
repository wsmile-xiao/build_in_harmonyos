#!/usr/bin/env python3
"""Smoke-test the installed ros-genlisp package layout."""

import os
import pathlib
import sys
import xml.etree.ElementTree as ET


def require_file(path):
    if not path.is_file():
        raise RuntimeError(f"Missing expected file: {path}")
    return path.read_text(encoding="utf-8")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: test_ros_genlisp.py <package-folder>")

    package_folder = pathlib.Path(sys.argv[1])
    share = package_folder / "share" / "ros-genlisp"
    python_pkg = package_folder / "lib" / "python" / "genlisp"

    package_xml = share / "package.xml"
    require_file(package_xml)
    root = ET.parse(package_xml).getroot()
    if root.findtext("name") != "genlisp" or root.findtext("version") != "0.4.18":
        raise RuntimeError("package.xml metadata does not match genlisp 0.4.18")

    require_file(share / "cmake" / "genlisp-extras.cmake.em")
    msg_template = require_file(share / "scripts" / "msg.lisp.template")
    srv_template = require_file(share / "scripts" / "srv.lisp.template")
    if "boost::python" not in msg_template or "boost::python" not in srv_template:
        raise RuntimeError("Templates do not contain expected boost::python bindings")
    if "export_" not in msg_template or "export_" not in srv_template:
        raise RuntimeError("Templates do not contain expected export functions")

    for filename in ("__init__.py", "generate.py", "genlisp_main.py"):
        require_file(python_pkg / filename)

    require_file(package_folder / "bin" / "gen_lisp.py")
    if os.environ.get("ROS_GENLISP_DIR") and pathlib.Path(os.environ["ROS_GENLISP_DIR"]) != share:
        raise RuntimeError("ROS_GENLISP_DIR does not point at the packaged share directory")

    print("ros-genlisp package checks passed: 8/8")


if __name__ == "__main__":
    main()
