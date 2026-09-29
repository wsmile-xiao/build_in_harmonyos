#!/usr/bin/env python3
"""test_package — undms 1.3 OHOS consumer.

Runs the packaged bin/undms on a generated two-track DMS image, compiles the
extracted disk into an aarch64 consumer program and executes it to verify
every byte (through qemu-aarch64 on x86 runners).
"""
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class UndmsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _runner(self):
        if str(self.settings.arch) == "armv8" and platform.machine().lower() not in ("aarch64", "arm64"):
            emulator = shutil.which("qemu-aarch64")
            if not emulator:
                raise RuntimeError("aarch64 consumer requires qemu-aarch64 on x86 runner")
            return [emulator]
        return []

    def build(self):
        folder = Path(self.build_folder)
        folder.mkdir(parents=True, exist_ok=True)
        fixture = folder / "two-tracks.dms"
        extracted = folder / "disk.img"
        subprocess.run([sys.executable, str(Path(self.source_folder) / "make_fixture.py"), str(fixture)], check=True)
        tool = Path(self.dependencies["undms"].package_folder) / "bin" / "undms"
        command = self._runner() + [str(tool), str(fixture), str(extracted)]
        subprocess.run(command, check=True)
        # The packaged CLI output is input to the OHOS consumer's compilation.
        data = extracted.read_bytes()
        if len(data) != 16384:
            raise RuntimeError("undms did not extract both tracks")
        (folder / "extracted_disk.h").write_text(
            "static const unsigned char disk_image[] = {\n" +
            ",".join(str(byte) for byte in data) + "\n};\n",
            encoding="ascii",
        )
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        consumer = Path(self.build_folder) / "test_undms"
        runner = "qemu-aarch64 " if self._runner() else ""
        self.run(f'{runner}"{consumer}"', env="conanrun")
