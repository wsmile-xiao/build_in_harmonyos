"""Native Conan tests, with optional HDC execution for a local cross build."""
import os
import shlex
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class BreezeGrubTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.user_presets_path = False
        if self.settings.os == "OHOS":
            toolchain.cache_variables["OHOS_ARCH"] = {
                "armv8": "arm64-v8a", "x86_64": "x86_64", "armv7": "armeabi-v7a"
            }[str(self.settings.arch)]
        toolchain.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        package = self.dependencies["breeze-grub"].package_folder
        hdc = os.environ.get("BREEZE_GRUB_HDC")
        suffix = ".exe" if self.settings.os == "Windows" else ""
        consumer = os.path.abspath(os.path.join(
            self.build_folder, self.cpp.build.bindirs[0], "test_breeze" + suffix))
        command = [sys.executable, os.path.join(self.recipe_folder, "run_tests.py"),
                   package, "--consumer", consumer]
        if hdc:
            if self.settings.os != "OHOS":
                raise ConanException("HDC execution requires an OHOS host profile")
            command.extend(["--hdc", hdc, "--target", os.environ.get("BREEZE_GRUB_HDC_TARGET", "")])
        elif not can_run(self):
            raise ConanException("Set BREEZE_GRUB_HDC to execute cross-built tests; tests cannot be skipped")
        elif self.settings.os == "OHOS":
            signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
            self.run(f"{shlex.quote(signer)} sign -inFile {shlex.quote(consumer)} "
                     f"-outFile {shlex.quote(consumer)} -selfSign 1", env="conanrun")
            command.append("--ohos")
        rendered = subprocess.list2cmdline(command) if os.name == "nt" else shlex.join(command)
        # Apply Conan's actual runtime metadata on the host even when the binary runs via HDC.
        with VirtualRunEnv(self).vars().apply():
            self.run(rendered, env=None if hdc else "conanrun")
