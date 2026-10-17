#!/usr/bin/env python3
"""Functional test for fastjar 0.98.

This script is referenced by test_package/conanfile.py and MANIFEST.yml
as the test source file. The actual test logic is in conanfile.py's test()
method which runs the fastjar binary directly.
"""
import os
import subprocess
import sys
import tempfile


def test_fastjar_version():
    """Test that fastjar --version works."""
    result = subprocess.run(["fastjar", "--version"], capture_output=True, text=True)
    assert result.returncode == 0, f"fastjar --version failed: {result.stderr}"
    assert "0.98" in result.stdout, f"Unexpected version output: {result.stdout}"
    print("PASS: fastjar --version works")


def test_fastjar_create_and_list():
    """Test that fastjar can create and list a JAR file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test file
        test_file = os.path.join(tmpdir, "hello.txt")
        with open(test_file, "w") as f:
            f.write("hello world\n")

        # Create a JAR
        jar_file = os.path.join(tmpdir, "test.jar")
        result = subprocess.run(
            ["fastjar", "cf", jar_file, test_file], capture_output=True, text=True
        )
        assert result.returncode == 0, f"fastjar cf failed: {result.stderr}"

        # List the JAR
        result = subprocess.run(
            ["fastjar", "tf", jar_file], capture_output=True, text=True
        )
        assert result.returncode == 0, f"fastjar tf failed: {result.stderr}"
        assert "hello.txt" in result.stdout, f"hello.txt not in JAR: {result.stdout}"
        print("PASS: fastjar create and list works")


if __name__ == "__main__":
    test_fastjar_version()
    test_fastjar_create_and_list()
    print("All tests passed!")
    sys.exit(0)
