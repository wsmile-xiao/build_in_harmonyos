import json
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class YatmTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("libao-pulse/1.2.2", run=True)
        self.requires("soundtouch/2.0.0", run=True)
        self.requires("slang/2.3.3", run=True)
        self.requires("libogg/1.3.6", run=True)

    def test(self):
        if not can_run(self):
            self.output.info("Skipping runtime test while cross-building")
            return

        shell_name = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        shell = shutil.which(shell_name) or shell_name
        package = self.dependencies["yatm"].package_folder
        binary = os.path.join(package, "bin", "yatm")
        script = os.path.join(self.source_folder, "test.sh")
        workdir = os.path.join(self.source_folder, "test-work")

        self.run(
            "%s %s %s %s" % (
                shlex.quote(shell),
                shlex.quote(script),
                shlex.quote(binary),
                shlex.quote(workdir),
            ),
            env="conanrun",
        )

        result = {
            "executed": True,
            "passed": True,
            "command": "yatm -q -e 0.1 test.wav with libao null driver",
            "discovered": 1,
            "passedCount": 1,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" +
            json.dumps(result, ensure_ascii=False)
        )

        upstream = {
            "status": "no_tests",
            "framework": "none",
            "command": "",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "yatm v0.9 contains no tests directory, CTest entries, assertions, or fixtures",
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" +
            json.dumps(upstream, ensure_ascii=False)
        )
