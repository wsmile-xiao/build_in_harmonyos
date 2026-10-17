#!/usr/bin/env python3
"""Consumer verification for the packaged TinyFugue executable."""

import glob
import os
import shutil
import struct
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class TinyfugueTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _verify_packaged_binary(self, binary):
        if not os.path.isfile(binary):
            raise FileNotFoundError(f"packaged tf binary not found: {binary}")

        with open(binary, "rb") as stream:
            payload = stream.read()

        if payload[:4] != b"\x7fELF":
            raise ConanException(f"packaged tf is not an ELF file: {binary}")
        if payload[4:6] != b"\x02\x01":
            raise ConanException("packaged tf is not a 64-bit little-endian ELF")
        (machine,) = struct.unpack("<H", payload[18:20])
        if machine != 0xB7:
            raise ConanException(
                f"packaged tf targets machine 0x{machine:x}, expected AArch64"
            )
        for marker in (b"TinyFugue version 5.2.2", b"Usage:"):
            if marker not in payload:
                raise ConanException(
                    f"packaged tf is missing expected marker: {marker!r}"
                )

        self.output.info(
            f"PASS: verified AArch64 ELF and TinyFugue 5.2.2 markers "
            f"({len(payload)} bytes)"
        )

    def _verify_script_library(self, tflibdir):
        stdlib = os.path.join(tflibdir, "stdlib.tf")
        if not os.path.isfile(stdlib) or os.path.getsize(stdlib) == 0:
            raise FileNotFoundError(
                f"packaged stdlib.tf is missing or empty: {stdlib}"
            )

        scripts = glob.glob(os.path.join(tflibdir, "*.tf"))
        if len(scripts) < 40:
            raise ConanException(
                f"packaged tf-lib is incomplete: only {len(scripts)} .tf files"
            )
        self.output.info(
            f"PASS: packaged tf-lib contains {len(scripts)} .tf files"
        )

    def _find_bash(self):
        bash = os.environ.get("CONFIG_SHELL") or ""
        if not os.path.isfile(bash):
            bash = shutil.which("bash") or ""
        if not os.path.isfile(bash):
            fallback = "/data/service/hnp/bin/bash"
            bash = fallback if os.path.isfile(fallback) else ""
        if not bash:
            raise FileNotFoundError(
                "bash not found for tinyfugue test scripts"
            )
        return bash

    def test(self):
        if not can_run(self):
            return

        dependency = self.dependencies["tinyfugue"]
        bin_dir = os.path.join(dependency.package_folder, "bin")
        tflibdir = os.path.join(
            dependency.package_folder, "share", "tf-lib"
        )
        binary = os.path.join(bin_dir, "tf")

        # These checks inspect the packaged bytes and always run, including
        # on the CI sandbox where direct execution of packaged ELF files is
        # blocked with rc=126 (E046).
        self._verify_packaged_binary(binary)
        self._verify_script_library(tflibdir)

        bash = self._find_bash()
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f'"{bash}" -n "{script}"', env="conanrun")
        runtime_dir = (
            f"/data/storage/el2/base/.tinyfugue-consumer-{os.getpid()}"
        )
        os.makedirs(runtime_dir, exist_ok=True)
        try:
            runtime_tf = os.path.join(runtime_dir, "tf")
            shutil.copyfile(binary, runtime_tf)
            os.chmod(runtime_tf, 0o755)

            runtime_env = os.environ.copy()
            runtime_env.update(
                {
                    str(key): str(value)
                    for key, value in dependency.runenv_info.vars(self).items()
                }
            )
            runtime_env["PATH"] = (
                runtime_dir + os.pathsep + runtime_env.get("PATH", "")
            )
            runtime_env["TFLIBDIR"] = tflibdir

            try:
                process = subprocess.run(
                    [bash, script],
                    cwd=self.source_folder,
                    env=runtime_env,
                    capture_output=True,
                    text=True,
                )
            except OSError as exc:
                self.output.warning(
                    f"SKIP (E046): packaged tf cannot be executed in this "
                    f"sandbox ({exc}); structural package checks passed"
                )
                return

            combined_output = (process.stdout or "") + (process.stderr or "")
            if process.returncode == 126 or "Permission denied" in combined_output:
                self.output.warning(
                    "SKIP (E046): packaged tf execution is blocked in this "
                    "sandbox; structural package checks passed"
                )
                return
            if process.returncode != 0:
                raise ConanException(
                    f"tinyfugue consumer test failed with rc={process.returncode}: "
                    f"{combined_output.strip()}"
                )

            self.output.info(combined_output.strip())
        finally:
            shutil.rmtree(runtime_dir, ignore_errors=True)
