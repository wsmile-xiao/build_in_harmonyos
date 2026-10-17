#!/usr/bin/env python3
"""Exercise dh-ros through its installed Python API and CLI."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from catkin_pkg.package import parse_package_string
from dhros.common import topological_sort


PACKAGE_XML = """<package format=\"3\">
  <name>consumer_demo</name>
  <version>1.2.3</version>
  <description>consumer test package</description>
  <maintainer email=\"test@example.invalid\">Consumer Test</maintainer>
  <license>MIT</license>
  <buildtool_depend>catkin</buildtool_depend>
</package>
"""


def resolve_rosbuilder():
    """Return an absolute path to the packaged ``rosbuilder`` console script.

    OHOS Python forces ``subprocess`` down the ``os.posix_spawn()`` path
    (knowledge E405), which does *not* search ``PATH``: a bare ``rosbuilder``
    raises ``FileNotFoundError`` even when the packaged ``bin`` directory is on
    ``PATH``. The recipe therefore passes the script's absolute path in
    ``DHROS_ROSBUILDER``; ``shutil.which`` is only a secondary fallback.
    """
    candidates = (os.environ.get("DHROS_ROSBUILDER"), shutil.which("rosbuilder"))
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return "rosbuilder"


ROSBUILDER = resolve_rosbuilder()


def main():
    package = parse_package_string(PACKAGE_XML)
    assert package.name == "consumer_demo"
    assert str(package.version) == "1.2.3"
    assert topological_sort({"consumer_demo": []}) == ["consumer_demo"]

    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory)
        (source / "package.xml").write_text(PACKAGE_XML, encoding="utf-8")
        detected = subprocess.run(
            [ROSBUILDER, "--detect", "--sourcedir", str(source)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert detected.returncode == 0, detected.stderr
        build_order = subprocess.run(
            [ROSBUILDER, "--build-order", "--sourcedir", str(source)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert build_order.returncode == 0, build_order.stderr
        assert build_order.stdout.strip() == "consumer_demo"

    help_result = subprocess.run(
        [ROSBUILDER, "--help"], check=False, capture_output=True, text=True
    )
    assert help_result.returncode == 0, help_result.stderr
    assert "--build-order" in help_result.stdout
    print("dh-ros consumer test passed")


if __name__ == "__main__":
    main()
