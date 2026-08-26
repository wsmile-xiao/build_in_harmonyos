#!/usr/bin/env python3
"""Functional test for the packaged AVR GCC bootstrap compiler."""

import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run


class AvrGccBootstrapTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    exports_sources = "smoke.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("avr-binutils/2.43.1")

    @property
    def _compiler_root(self):
        return self.dependencies[
            "avr-gcc-bootstrap"
        ].package_folder

    @property
    def _binutils_root(self):
        return self.dependencies.build["avr-binutils"].package_folder

    def _tool(self, root, name):
        path = os.path.join(root, "bin", name)
        if not os.path.isfile(path):
            raise ConanInvalidConfiguration(
                "Packaged tool was not found: {}".format(path)
            )
        return path

    def _run_capture(self, command):
        environment = os.environ.copy()
        binutils_bin = os.path.join(self._binutils_root, "bin")
        environment["PATH"] = (
            binutils_bin
            + os.pathsep
            + environment.get("PATH", "")
        )
        result = subprocess.run(
            command,
            cwd=self.build_folder,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        output = result.stdout + result.stderr
        if output.strip():
            self.output.info(output.strip())
        result.check_returncode()
        return output

    def _target_dispatcher_bin(self, build):
        root = build / ".avr-binutils-dispatch"
        bin_dir = root / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        for name in ("as", "ld", "nm"):
            shutil.copy2(
                self._tool(self._binutils_root, "avr-{}".format(name)),
                bin_dir / name,
            )

        source_scripts = (
            Path(self._binutils_root) / "avr" / "lib" / "ldscripts"
        )
        if not source_scripts.is_dir():
            raise ConanInvalidConfiguration(
                "AVR linker scripts were not found: {}".format(
                    source_scripts
                )
            )
        shutil.copytree(
            source_scripts,
            root / "avr" / "lib" / "ldscripts",
            dirs_exist_ok=True,
        )
        return bin_dir

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross-building: packaged OHOS host compiler cannot run"
            )
            return

        temp_root = Path(os.environ.get("TMPDIR", self.build_folder))
        temp_root.mkdir(parents=True, exist_ok=True)
        build = Path(
            tempfile.mkdtemp(
                prefix="avr-gcc-bootstrap-test-",
                dir=str(temp_root),
            )
        )
        source = Path(self.source_folder) / "smoke.c"
        elf = build / "smoke.elf"
        dispatcher_bin = self._target_dispatcher_bin(build)

        compiler = self._tool(self._compiler_root, "avr-gcc")
        objdump = self._tool(self._binutils_root, "avr-objdump")
        nm = self._tool(self._binutils_root, "avr-nm")
        size = self._tool(self._binutils_root, "avr-size")

        self.run(
            "{} --version".format(shlex.quote(compiler)),
            env="conanrun",
        )
        version = self._run_capture([compiler, "--version"])
        if "14.2.0" not in version:
            raise ConanInvalidConfiguration(
                "Unexpected avr-gcc version: {}".format(
                    version.splitlines()[0]
                )
            )

        libgcc_output = self._run_capture(
            [
                compiler,
                "-B{}{}".format(dispatcher_bin, os.sep),
                "-mmcu=atmega328p",
                "-print-libgcc-file-name",
            ]
        )
        libgcc = os.path.realpath(libgcc_output.strip().splitlines()[-1])
        compiler_root = os.path.realpath(self._compiler_root)
        if not os.path.isfile(libgcc):
            raise ConanInvalidConfiguration(
                "avr-gcc did not resolve libgcc.a: {}".format(libgcc)
            )
        if os.path.commonpath([compiler_root, libgcc]) != compiler_root:
            raise ConanInvalidConfiguration(
                "avr-gcc selected libgcc outside its package: {}".format(
                    libgcc
                )
            )

        multidir = self._run_capture(
            [
                compiler,
                "-B{}{}".format(dispatcher_bin, os.sep),
                "-mmcu=atmega328p",
                "-print-multi-directory",
            ]
        ).strip()
        if not multidir:
            raise ConanInvalidConfiguration(
                "avr-gcc returned an empty multilib directory"
            )

        self._run_capture(
            [
                compiler,
                "-B{}{}".format(dispatcher_bin, os.sep),
                "-mmcu=atmega328p",
                "-Os",
                "-nostdlib",
                "-Wl,-e,main",
                str(source),
                "-lgcc",
                "-o",
                str(elf),
            ]
        )

        file_header = self._run_capture([objdump, "-f", str(elf)])
        if "file format elf32-avr" not in file_header:
            raise ConanInvalidConfiguration(
                "avr-objdump did not identify elf32-avr"
            )
        if "architecture: avr" not in file_header:
            raise ConanInvalidConfiguration(
                "avr-objdump did not identify the AVR architecture"
            )

        symbols = self._run_capture([nm, str(elf)])
        if " T main" not in symbols:
            raise ConanInvalidConfiguration(
                "Linked AVR ELF does not export main"
            )
        if "__udivmodhi4" not in symbols:
            raise ConanInvalidConfiguration(
                "Linked AVR ELF did not consume packaged libgcc division code"
            )

        self._run_capture([size, str(elf)])
        self.output.info(
            "PASS: packaged AVR GCC bootstrap functional smoke test"
        )
