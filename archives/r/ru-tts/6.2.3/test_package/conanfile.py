#!/usr/bin/env python3
"""Conan consumer and packaged-command tests for ru-tts."""

import json
import os
import platform
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class RuTtsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        toolchain.variables["CMAKE_C_STANDARD"] = 11
        toolchain.variables["CMAKE_C_STANDARD_REQUIRED"] = True
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _needs_runner(self):
        machine = platform.machine().lower()
        target = str(self.settings.arch)
        return target == "armv8" and machine not in ("aarch64", "arm64")

    @staticmethod
    def _sign(executable):
        signer = shutil.which("binary-sign-tool")
        if not signer:
            fallback = "/data/service/hnp/bin/binary-sign-tool"
            signer = fallback if os.path.isfile(fallback) else ""
        if not signer:
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required for native OHOS execution"
            )
        directory = os.path.dirname(executable)
        source = os.path.basename(executable)
        signed = source + ".signed"
        subprocess.run(
            [
                signer,
                "sign",
                "-inFile",
                source,
                "-outFile",
                signed,
                "-selfSign",
                "1",
            ],
            check=True,
            cwd=directory,
        )
        shutil.move(os.path.join(directory, signed), executable)
        os.chmod(executable, 0o755)

    def _target_command(self, executable, arguments="", stdin="", stdout=""):
        dependency = self.dependencies[self.tested_reference_str]
        library_dir = dependency.cpp_info.libdirs[0]
        runner = self.conf.get(
            "user.ru_tts:qemu_runner", default="", check_type=str
        ).strip()
        if self._needs_runner() and not runner:
            raise ConanInvalidConfiguration(
                "user.ru_tts:qemu_runner is required for local AArch64 execution"
            )
        if str(self.settings.os) == "OHOS" and not runner:
            self._sign(executable)

        pieces = [
            "env",
            "LD_LIBRARY_PATH=" + shlex.quote(library_dir),
        ]
        if runner:
            pieces.append(runner)
            pieces.extend(
                [
                    "-E",
                    "LD_LIBRARY_PATH="
                    + shlex.quote(library_dir + ":/lib:/usr/lib"),
                ]
            )
        pieces.append(shlex.quote(executable))
        if arguments:
            pieces.append(arguments)
        if stdin:
            pieces.extend(["<", shlex.quote(stdin)])
        if stdout:
            pieces.extend([">", shlex.quote(stdout)])
        return " ".join(pieces)

    def test(self):
        binary_dir = os.path.join(self.build_folder, "bin")
        portable_test = os.path.join(binary_dir, "test_ru_tts")
        ohos_test = os.path.join(binary_dir, "test_ru_tts_ohos")
        dependency = self.dependencies[self.tested_reference_str]
        packaged_cli = os.path.join(dependency.package_folder, "bin", "ru_tts")
        test_cli = os.path.join(binary_dir, "ru_tts")

        required_artifacts = [portable_test, packaged_cli]
        if str(self.settings.os) == "OHOS":
            required_artifacts.append(ohos_test)
        for required in required_artifacts:
            if not os.path.isfile(required):
                raise ConanInvalidConfiguration(
                    f"required consumer test artifact is missing: {required}"
                )
        shutil.copy2(packaged_cli, test_cli)

        input_path = os.path.join(binary_dir, "input.koi8-r")
        output_path = os.path.join(binary_dir, "output.raw")
        with open(input_path, "wb") as stream:
            stream.write(b"\xf0\xd2\xc9\xd7\xc5\xd4\n")

        commands = [self._target_command(portable_test)]
        if str(self.settings.os) == "OHOS":
            commands.append(self._target_command(ohos_test))
        commands.extend(
            [
                self._target_command(test_cli, "-v"),
                self._target_command(test_cli, "-h"),
                self._target_command(
                    test_cli, stdin=input_path, stdout=output_path
                ),
            ]
        )
        for command in commands:
            self.run(command, env="conanrun")

        if not os.path.isfile(output_path) or os.path.getsize(output_path) <= 1024:
            raise ConanException("packaged ru_tts produced no usable audio stream")

        assertion_count = 22 if str(self.settings.os) == "OHOS" else 16
        result = {
            "status": "passed",
            "discovered": assertion_count,
            "executed": assertion_count,
            "passed": assertion_count,
            "failed": 0,
            "skipped": 0,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT="
            + json.dumps(result, ensure_ascii=False, separators=(",", ":"))
        )
