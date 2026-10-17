#!/usr/bin/env python3
"""Conan test_package for ydotool (application package) — consumer contract tests.

Builds a tiny AF_UNIX datagram peer (mock_daemon) that implements the
ydotoold-side wire protocol, then drives the packaged `ydotool` client against
it and asserts the exact `struct input_event` byte stream. It also exercises
the CLI contract, the packaged daemon's real /dev/uinput behaviour, and
negative controls. test.sh performs the 16 assertions listed in MANIFEST.yml.

`conan create` executes this automatically (CI L1a checks the trace).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class YdotoolTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
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
            return
        dep = self.dependencies["ydotool"]
        bindir = os.path.join(dep.package_folder, "bin")
        ydotool_bin = os.path.join(bindir, "ydotool")
        ydotoold_bin = os.path.join(bindir, "ydotoold")
        for binary in (ydotool_bin, ydotoold_bin):
            if not os.path.exists(binary):
                raise Exception(f"expected packaged binary not found: {binary}")
        mock = os.path.join(self.build_folder, "mock_daemon")
        if not os.path.exists(mock):
            alt = os.path.join(self.build_folder, "Release", "mock_daemon")
            if os.path.exists(alt):
                mock = alt
        if not os.path.exists(mock):
            raise Exception(f"mock daemon was not built: {mock}")
        test_script = os.path.join(self.source_folder, "test.sh")
        # OHOS: /system/bin/sh (mksh) cannot run ELF binaries; bash runs the assertions.
        bash = os.environ.get("CONFIG_SHELL") or "bash"
        self.run(
            f'YDOTOOL_BIN="{ydotool_bin}" YDOTOOLD_BIN="{ydotoold_bin}" '
            f'MOCK_DAEMON="{mock}" {bash} "{test_script}"',
            env="conanrun",
        )
        self.output.info("ydotool consumer tests finished (test.sh: 16 designed assertions; "
                         "platform-restricted wire-protocol assertions are reported as skipped, "
                         "see the test.sh summary line)")
