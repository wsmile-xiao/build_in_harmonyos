#!/usr/bin/env python3
"""Consumer test for the bandwidthd command-line package."""

import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile


class BandwidthdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        shell = "/bin/sh" if self.settings.os == "OHOS" else "sh"
        if self.settings.os != "OHOS":
            self.run(f'{shell} test.sh', env="conanrun")
            return

        # OHOS rejects unsigned ELF files from HMDFS even when mode 0755 is
        # present. Stage the Conan-installed executable in the worker's
        # writable app-local filesystem and apply the worker self-signature
        # before exercising the real packaged CLI.
        package_binary = Path(self.dependencies["bandwidthd"].package_folder) / "bin" / "bandwidthd"
        runtime_dir = Path("/data/storage/el1/base") / f"bandwidthd-test-{os.getpid()}"
        runtime_binary = runtime_dir / "bandwidthd"
        signed_binary = runtime_dir / "bandwidthd.signed"
        runtime_dir.mkdir(parents=True, exist_ok=False)
        try:
            shutil.copy2(package_binary, runtime_binary)
            subprocess.run(
                ["/data/service/hnp/bin/llvm-objcopy", "--remove-section", ".codesign", str(runtime_binary)],
                check=True,
            )
            subprocess.run(
                [
                    "/data/service/hnp/bin/binary-sign-tool",
                    "sign",
                    "-inFile",
                    str(runtime_binary),
                    "-outFile",
                    str(signed_binary),
                    "-selfSign",
                    "1",
                ],
                check=True,
            )
            signed_binary.replace(runtime_binary)
            os.chmod(runtime_binary, 0o755)
            self.run(
                f'BANDWIDTHD_TEST_BINARY="{runtime_binary}" '
                f'TMPDIR="{runtime_dir}" {shell} test.sh',
                env="conanrun",
            )
        finally:
            shutil.rmtree(runtime_dir, ignore_errors=True)
