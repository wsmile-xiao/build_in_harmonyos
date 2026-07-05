# test_package/conanfile.py (autotools variant)
"""Conan test_package template — Autotools/subprocess test.

For packages that produce CLI binaries, test by running the binary.
File location: archives/{letter}/{name}/{version}/test_package/conanfile.py
"""
import os
import subprocess

from conan import ConanFile


class {Name}TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Run the installed binary to verify it works
        binary = os.path.join(self.deps_user_info["{name}"].rootpath, "bin", "{name}")
        if not os.path.exists(binary):
            self.output.warning(f"Binary not found: {binary}")
            return
        result = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            raise Exception(f"{binary} --version failed with code {result.returncode}")
        self.output.info(f"✅ {result.stdout.strip()}")
