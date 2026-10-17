#!/usr/bin/env python3
"""Conan consumer test for kea-ctrl-agent 3.0.3.

Three checks run against the packaged agent:

* ``test_kea_ctrl_agent.py`` — consumer contract: version/usage/config-check
  output, the ``-t`` error paths and one real control-channel exchange (start
  the agent on a loopback port, POST ``config-get`` over HTTP, verify the JSON
  answer and the unsupported-command error answer, stop via SIGTERM - proves
  the process loads its Kea runtime libraries and serves the control channel);
* ``test_ohos_platform``     — HarmonyOS-specific: the packaged executable
  carries the OHOS aarch64 / musl / libc++ platform ABI signature;
* ``test_ohos_runtime``      — HarmonyOS-specific: the packaged Kea runtime
  closure (libkea-*.so*) is resolvable by the OHOS loader and the agent runs.
"""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class KeaCtrlAgentTestConan(ConanFile):
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
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: kea-ctrl-agent consumer tests skipped")
            return

        agent = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder,
            "bin", "kea-ctrl-agent")
        bindir = self.cpp.build.bindirs[0]

        self.run('"{}/test_ohos_platform" "{}"'.format(bindir, agent),
                 env="conanrun")
        self.run('"{}/test_ohos_runtime" "{}"'.format(bindir, agent),
                 env="conanrun")

        test_script = os.path.join(self.source_folder, "test_kea_ctrl_agent.py")
        self.run('"{}" "{}"'.format(sys.executable, test_script), env="conanrun")
