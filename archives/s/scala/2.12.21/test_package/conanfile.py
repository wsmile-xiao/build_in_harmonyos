#!/usr/bin/env python3
"""Conan test_package — Scala 2.12.21 (JVM precompiled distribution).

Verifies that the Scala tools (scala, scalac, scaladoc, scalap, fsc)
are installed and functional via smoke tests.
"""
import os

from conan import ConanFile


class ScalaTestConan(ConanFile):
    """test_package for Scala JVM toolset — runs test.sh which invokes scala tools."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        import shutil
        # Find bash dynamically for script execution
        bash = shutil.which("bash") or shutil.which("sh") or "/bin/sh"
        
        # Get the scala package's bin directory from dependency info
        scala_bin = os.path.join(self.dependencies["scala"].package_folder, "bin")
        
        # Also find java for the scala scripts
        java_bin = ""
        java_home = os.environ.get("JAVA_HOME", "")
        if java_home:
            java_bin = os.path.join(java_home, "bin")
        
        # Build the test command with explicit PATH
        env_path = f"PATH={scala_bin}:{java_bin}:$PATH"
        self.run(f'{env_path} "{bash}" test.sh', env="conanrun")
