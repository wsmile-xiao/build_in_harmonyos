#!/usr/bin/env python3
"""Consumer test for the packaged dh-ros command and Python API."""

import os
import shlex
import sys

from conan import ConanFile


class DhRosTestConan(ConanFile):
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # catkin_pkg ships inside the dh-ros package (bundled from pip during
        # build), so it is deliberately not declared as a separate requirement.
        self.requires(self.tested_reference_str)
        self.requires("perl/5.42.2.3")

    def test(self):
        script = os.path.join(os.path.dirname(__file__), "test_consumer.py")
        python_paths = []
        relative_paths = (
            os.path.join("lib", "site-packages"),
            os.path.join("lib", "python3.12", "site-packages"),
            os.path.join(
                "lib",
                f"python{sys.version_info.major}.{sys.version_info.minor}",
                "site-packages",
            ),
            "site-packages",
        )
        rosbuilder = None
        for dependency in self.dependencies.values():
            if not dependency.package_folder:
                continue
            candidate = os.path.join(dependency.package_folder, "bin", "rosbuilder")
            if rosbuilder is None and os.path.isfile(candidate):
                rosbuilder = candidate
            for relative_path in relative_paths:
                path = os.path.join(dependency.package_folder, relative_path)
                if os.path.isdir(path) and path not in python_paths:
                    python_paths.append(path)
        if not python_paths:
            raise RuntimeError("No Conan dependency Python site-packages directory found")
        if rosbuilder is None:
            raise RuntimeError("Packaged rosbuilder console script not found")
        pythonpath = os.pathsep.join(python_paths)
        # OHOS Python routes subprocess through os.posix_spawn() (knowledge E405),
        # which never searches PATH: a bare "rosbuilder" raises FileNotFoundError
        # even when the packaged bin dir is on PATH. Hand the absolute path to the
        # consumer test so it exercises the real console script.
        command = (
            f"DHROS_ROSBUILDER={shlex.quote(rosbuilder)} "
            f"PYTHONPATH={shlex.quote(pythonpath)}:${{PYTHONPATH:-}} "
            f"{shlex.quote(sys.executable)} {shlex.quote(script)}"
        )
        self.run(command, env="conanrun")
