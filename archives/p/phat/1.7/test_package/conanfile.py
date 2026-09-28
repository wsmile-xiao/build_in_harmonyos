#!/usr/bin/env python3
"""Conan consumer tests — PHAT 1.7."""

import json
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, cmake_layout


class PhatTestConan(ConanFile):
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
            "user.phat:qemu_runner", default="", check_type=str
        ).strip()
        for name in ("test_phat", "test_phat_ohos"):
            executable = os.path.join(bindirs[0], name)
            self._run_target(executable, runner)
        self._test_cli(runner)
        result = {
            "status": "passed",
            "discovered": 3,
            "executed": 3,
            "passed": 3,
            "failed": 0,
            "skipped": 0,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT="
            + json.dumps(result, ensure_ascii=False, separators=(",", ":"))
        )

    def _test_cli(self, runner):
        dependency_bindirs = self.dependencies["phat"].cpp_info.bindirs
        if not dependency_bindirs:
            raise ConanInvalidConfiguration("packaged phat executable is unavailable")
        source_binary = os.path.join(
            self.dependencies["phat"].package_folder,
            dependency_bindirs[0],
            "phat",
        )
        executable = os.path.join(self.build_folder, "phat-cli-test")
        shutil.copy2(source_binary, executable)
        os.chmod(executable, 0o755)
        matrix = os.path.join(self.build_folder, "triangle.dat")
        pairs = os.path.join(self.build_folder, "triangle-pairs.dat")
        with open(matrix, "w", encoding="utf-8") as stream:
            stream.write("0\n0\n0\n1 0 1\n1 0 2\n1 1 2\n2 3 4 5\n")
        if str(self.settings.os) == "OHOS" and not runner:
            self._sign(executable)
        command = "{} {} --ascii {} {}".format(
            runner,
            shlex.quote(executable),
            shlex.quote(matrix),
            shlex.quote(pairs),
        ).strip()
        self.run(command, env="conanrun")
        with open(pairs, "r", encoding="utf-8") as stream:
            output = [line.strip() for line in stream if line.strip()]
        expected = ["3", "1 3", "2 4", "5 6"]
        if output != expected:
            raise ConanInvalidConfiguration(
                f"unexpected phat CLI output: {output!r}"
            )

    def _run_target(self, executable, runner):
        if not os.path.isfile(executable):
            raise ConanInvalidConfiguration(
                f"consumer test executable missing: {executable}"
            )
        if str(self.settings.os) == "OHOS" and not runner:
            self._sign(executable)
        command = "{} {}".format(runner, shlex.quote(executable)).strip()
        self.run(command, env="conanrun")

    @staticmethod
    def _sign(executable):
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
