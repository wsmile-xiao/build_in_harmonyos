#!/usr/bin/env python3
"""Consumer tests for the packaged spew command suite."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException


class SpewTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["spew"]
        bindir = package.cpp_info.bindirs[0]
        script = os.path.join(self.build_folder, "test.sh")
        if self.settings.os != "OHOS":
            # test.sh uses `set -o pipefail`, so it must run under a real bash;
            # /bin/sh may be dash. The script runs on the build host machine.
            shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "bash"
            self.run(
                f'BINDIR={bindir} TMPDIR={self.build_folder} "{shell}" {script}',
                env="conanrun",
            )
            return

        private_tmp = os.path.join(
            "/data/storage/el2/base", f"spew-test-{os.getpid()}"
        )
        os.makedirs(private_tmp, exist_ok=True)
        env = os.environ.copy()
        env["BINDIR"] = bindir
        env["TMPDIR"] = private_tmp
        bash = env.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        result = subprocess.run(
            [bash, script],
            cwd=private_tmp,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=120,
        )
        self.output.info(result.stdout)
        if result.returncode != 0:
            raise ConanException(f"spew consumer tests failed: {result.returncode}")
