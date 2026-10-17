#!/usr/bin/env python3
"""Conan consumer tests — paryfor 0.1."""

import json
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, cmake_layout


class ParyforTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise ConanInvalidConfiguration("consumer test bindir is unavailable")
        runner = self.conf.get(
            "user.paryfor:qemu_runner", default="", check_type=str
        ).strip()
        for name in ("test_paryfor", "test_paryfor_ohos"):
            executable = os.path.join(bindirs[0], name)
            if not os.path.isfile(executable):
                raise ConanInvalidConfiguration(f"consumer test executable missing: {executable}")
            if str(self.settings.os) == "OHOS" and not runner:
                self._sign(executable)
            command = "{} {}".format(runner, shlex.quote(executable)).strip()
            self.run(command, env="conanrun")
        result = {
            "status": "passed",
            "discovered": 2,
            "executed": 2,
            "passed": 2,
            "failed": 0,
            "skipped": 0,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT="
            + json.dumps(result, ensure_ascii=False, separators=(",", ":"))
        )

    @staticmethod
    def _sign(executable):
        """Sign an OHOS executable before running it on a native worker."""
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required to execute consumer tests on OHOS"
            )
        directory = os.path.dirname(executable)
        unsigned_name = os.path.basename(executable)
        signed_name = unsigned_name + ".signed"
        signed = os.path.join(directory, signed_name)
        subprocess.run(
            [signer, "sign", "-inFile", unsigned_name, "-outFile", signed_name,
             "-selfSign", "1"],
            check=True,
            cwd=directory,
        )
        shutil.move(signed, executable)
        os.chmod(executable, 0o755)
