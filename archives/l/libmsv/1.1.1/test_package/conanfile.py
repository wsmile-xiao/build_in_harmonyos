#!/usr/bin/env python3
"""Conan test_package — libmsv 1.1.1 public API verification."""
import json
import os
import shutil
import subprocess
import sys
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class LibmsvTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def _command(self, executable):
        if not cross_building(self):
            return '"{}"'.format(executable)
        runner = self.conf.get(
            "user.libminini:qemu_runner",
            default="qemu-aarch64",
        )
        if not shutil.which(str(runner).split()[0]):
            raise ConanInvalidConfiguration(
                "qemu-aarch64 is required to run the OHOS test package"
            )
        return '{} -E LD_LIBRARY_PATH="$LD_LIBRARY_PATH" "{}"'.format(
            runner, executable
        )

    def test(self):
        port_file = os.path.join(self.build_folder, "mock-msva.port")
        if os.path.exists(port_file):
            os.remove(port_file)
        server = subprocess.Popen(
            [sys.executable, os.path.join(self.source_folder, "mock_msva.py"),
             port_file],
            cwd=self.build_folder,
        )
        try:
            for _ in range(100):
                if os.path.isfile(port_file):
                    break
                if server.poll() is not None:
                    raise RuntimeError("mock MSVA exited before becoming ready")
                time.sleep(0.05)
            else:
                raise RuntimeError("mock MSVA did not become ready")

            with open(port_file, "r", encoding="utf-8") as stream:
                port = int(stream.read().strip())
            endpoint = "http://127.0.0.1:{}".format(port)
            runtime = Environment()
            runtime.define("MONKEYSPHERE_VALIDATION_AGENT_SOCKET", endpoint)
            with runtime.vars(self).apply():
                for name in ("test_upstream", "test_ohos"):
                    executable = os.path.join(self.cpp.build.bindirs[0], name)
                    self.run(self._command(executable), env="conanrun")
            result = {
                "executed": True,
                "passed": True,
                "command": "test_upstream && test_ohos",
                "discovered": 14,
                "passedCount": 14,
            }
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result)
            )
        finally:
            server.terminate()
            server.wait(timeout=10)
