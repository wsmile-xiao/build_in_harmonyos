#!/usr/bin/env python3
"""Run a real Redis server and exercise it through redis-cli."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration


class RedisTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    exports_sources = "test.sh"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash")
        if not bash and str(self.settings.os) == "OHOS":
            for candidate in (
                "/data/service/hnp/bin/bash",
                "/storage/Users/currentUser/usr/local/bin/bash",
            ):
                if os.path.isfile(candidate):
                    bash = candidate
                    break
        if not bash:
            raise ConanInvalidConfiguration("bash is required for the Redis service test")

        script = os.path.join(self.source_folder, "test.sh")
        self.run(
            f"{shlex.quote(bash)} {shlex.quote(script)}",
            cwd=self.source_folder,
            env="conanrun",
        )
