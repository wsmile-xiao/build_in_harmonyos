#!/usr/bin/env python3
"""Conan test_package — reflex 20241231 consumer verification.

Drives the real consumer workflow through ``test_reflex.py``: the packaged
generator is used to emit a C scanner and a C++ scanner, both are compiled
against the packaged header/library and executed, and the token streams they
produce are asserted.  A final artefact check confirms the manual page made
it into the package.

Seven behavioural checks, each printing one ``SMOKE-PASS <name>`` line; the
per-check count is reported through the ``HMBS_TEST_PACKAGE_RESULT`` marker
and a non-zero exit fails ``conan create``.
"""
import json
import os
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run

CONSUMER_CHECK_COUNT = 7


class ReflexTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _compiler(self, lang):
        """Compiler for ``lang`` (c/cpp), mirroring the main recipe's
        toolchain lookup so the consumer compiles with the same toolchain."""
        execs = self.conf.get("tools.build:compiler_executables",
                              default={}, check_type=dict) or {}
        fallback = "clang++" if lang == "cpp" else "clang"
        return execs.get(lang) or fallback

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: skip runtime execution")
            return

        dep = self.dependencies["reflex"]
        script = os.path.join(self.source_folder, "test_reflex.py")
        python = os.environ.get("HMBS_PYTHON3") or sys.executable or "python3"

        # L0d: real execution through Conan — a non-zero exit fails the package.
        self.run('"{0}" "{1}" "{2}" "{3}" "{4}"'.format(
            python, script, dep.package_folder,
            self._compiler("c"), self._compiler("cpp")), env="conanrun")

        # Capture the same run to count the deterministic SMOKE-PASS evidence
        # lines (the capture subprocess does not inherit conanrun, so PATH is
        # extended explicitly to keep the two runs identical).
        capture_env = dict(os.environ)
        capture_env["PATH"] = os.pathsep.join([
            os.path.join(dep.package_folder, "bin"),
            capture_env.get("PATH", ""),
        ])
        proc = subprocess.run(
            [python, script, dep.package_folder,
             self._compiler("c"), self._compiler("cpp")],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=900,
            env=capture_env,
        )
        output = proc.stdout or ""
        self.output.info(output[-4000:])

        ok_count = sum(1 for line in output.splitlines()
                       if line.startswith("SMOKE-PASS "))
        marker = {
            "executed": True,
            "passed": proc.returncode == 0 and ok_count == CONSUMER_CHECK_COUNT,
            "command": ("python3 test_reflex.py <package_folder> <cc> <cxx> "
                        "(version + C/C++ scanner end-to-end + artefacts)"),
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": ok_count,
        }
        marker_msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker)
        self.output.info(marker_msg)
        print(marker_msg, flush=True)
        if not marker["passed"]:
            raise ConanException(
                "consumer test failed: rc={0} ok={1}/{2}".format(
                    proc.returncode, ok_count, CONSUMER_CHECK_COUNT))
