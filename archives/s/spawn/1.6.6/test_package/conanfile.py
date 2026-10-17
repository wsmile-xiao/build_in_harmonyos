#!/usr/bin/env python3
"""Consumer test for the installed spawn-fcgi binary.

The test compiles a tiny FastCGI responder and then runs the packaged
spawn-fcgi.  The Python harness performs a real loopback socket and FastCGI
request/response exchange; HMBS markers are based on its CHECK-OK lines.
"""
import glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import copy


CONSUMER_CHECK_COUNT = 7
_OHOS_LLVM_GLOB = "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/clang"


def _resolve_cc(conf_value):
    candidates = [
        conf_value,
        os.environ.get("CC"),
        shutil.which("clang"),
        shutil.which("cc"),
        "/data/service/hnp/bin/clang",
    ]
    candidates.extend(sorted(glob.glob(_OHOS_LLVM_GLOB)))
    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    raise ConanInvalidConfiguration(
        "no executable C compiler found for spawn test_package; conf=%r PATH=%r"
        % (conf_value, os.environ.get("PATH"))
    )


class SpawnTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        if os.path.normpath(self.source_folder) != os.path.normpath(
            self.build_folder
        ):
            copy(self, "fcgi_backend.c", self.source_folder, self.build_folder)
            copy(self, "test_spawn_fcgi.py", self.source_folder, self.build_folder)

    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = _resolve_cc(compilers.get("c", "clang"))
        backend = os.path.join(self.build_folder, "fcgi_backend")
        source = os.path.join(self.build_folder, "fcgi_backend.c")
        self.run(
            '"%s" -O2 -Wall -Wextra "%s" -o "%s"'
            % (cc, source, backend),
            env="conanbuild",
        )

    def test(self):
        if not can_run(self):
            raise ConanInvalidConfiguration(
                "spawn test_package can only run on the target OHOS machine"
            )

        binary = os.path.join(
            self.dependencies["spawn"].package_folder, "bin", "spawn-fcgi"
        )
        backend = os.path.join(self.build_folder, "fcgi_backend")
        harness = os.path.join(self.build_folder, "test_spawn_fcgi.py")
        python3 = os.environ.get("HMBS_PYTHON3") or shutil.which("python3")
        if not python3:
            python3 = "python3"

        # Keep the required self.run() checks visible in the conan create log;
        # the harness repeats both with captured output and assertions.
        self.run('"%s" -v' % binary, env="conanrun")
        self.run('"%s" -h' % binary, env="conanrun")

        command = [
            python3,
            harness,
            "--spawn-fcgi",
            binary,
            "--backend",
            backend,
        ]
        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=60,
            env=dict(os.environ),
        )
        output = proc.stdout or ""
        self.output.info(output[-5000:])
        passed_count = output.count("CHECK-OK:")
        passed = proc.returncode == 0 and passed_count == CONSUMER_CHECK_COUNT

        package_marker = {
            "executed": True,
            "passed": passed,
            "command": "python3 test_spawn_fcgi.py --spawn-fcgi <installed>/bin/spawn-fcgi --backend <built>/fcgi_backend",
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": passed_count,
        }
        upstream_marker = {
            "status": "no_tests",
            "framework": "meson",
            "command": "meson test",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "spawn-fcgi 1.6.6 meson.build defines no test() call, no "
                "tests directory, and no test program; audit is recorded in "
                "test_package/MANIFEST.yml"
            ),
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(package_marker, ensure_ascii=False)
        )
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker, ensure_ascii=False)
        )
        self.output.info(
            "TEST_PACKAGE_RESULT total=%d passed=%d failed=%d"
            % (CONSUMER_CHECK_COUNT, passed_count, CONSUMER_CHECK_COUNT - passed_count)
        )

        if not passed:
            raise ConanException(
                "spawn consumer test failed: rc=%s checks=%s/%s"
                % (proc.returncode, passed_count, CONSUMER_CHECK_COUNT)
            )
