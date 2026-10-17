#!/usr/bin/env python3
"""Consumer checks for the packaged zBoy executable and HarmonyOS SDL path."""

import os
import shutil
import tempfile

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ZboyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("sdl2/2.30.10")

    def layout(self):
        cmake_layout(self)

    def build(self):
        if str(self.settings.os) != "OHOS":
            return
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"])

    def _test_copy(self, source, temp_dir):
        if str(self.settings.os) != "OHOS":
            return source
        target = os.path.join(temp_dir, os.path.basename(source))
        shutil.copy2(source, target)
        os.chmod(target, 0o755)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise RuntimeError("HarmonyOS binary-sign-tool is required to execute test binaries")
        if os.path.isfile(objcopy):
            self.run(
                '"{}" --remove-section .codesign "{}"'.format(objcopy, target),
                ignore_errors=True,
            )
        signed = target + ".signed"
        self.run(
            '"{}" sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
                signer, target, signed
            )
        )
        if not os.path.isfile(signed):
            raise RuntimeError("HarmonyOS signer did not produce a signed test executable")
        shutil.move(signed, target)
        os.chmod(target, 0o755)
        return target

    def test(self):
        package = self.dependencies["zboy"]
        executable_name = "zboy.exe" if str(self.settings.os) == "Windows" else "zboy"
        executable = os.path.join(package.package_folder, "bin", executable_name)
        if not os.path.isfile(executable):
            raise AssertionError("zBoy executable missing from package: " + executable)

        if not can_run(self):
            self.output.warning(
                "Cross-built zBoy cannot run on this build host; native HarmonyOS runtime "
                "checks are executed on the OHOS/armv8 device profile."
            )
            return

        temp_dir = tempfile.mkdtemp(prefix="zboy-test-")
        try:
            executable = self._test_copy(executable, temp_dir)
            version_log = os.path.join(self.build_folder, "zboy-version.txt")
            help_log = os.path.join(self.build_folder, "zboy-help.txt")
            self.run(
                '"{}" --version > "{}" 2>&1'.format(executable, version_log),
                env="conanrun",
            )
            with open(version_log, "r", encoding="utf-8", errors="replace") as output:
                version_text = output.read()
            if "zBoy 0.71" not in version_text:
                raise AssertionError("unexpected zBoy --version output: " + version_text)

            self.run(
                '"{}" --help > "{}" 2>&1'.format(executable, help_log),
                env="conanrun",
            )
            with open(help_log, "r", encoding="utf-8", errors="replace") as output:
                help_text = output.read()
            if "COMMAND-LINE USAGE:" not in help_text.upper():
                raise AssertionError("unexpected zBoy --help output: " + help_text)

            if str(self.settings.os) == "OHOS":
                sdl_test = os.path.join(self.build_folder, "bin", "zboy_ohos_sdl_test")
                sdl_test = self._test_copy(sdl_test, temp_dir)
                self.run('"{}"'.format(sdl_test), env="conanrun")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
