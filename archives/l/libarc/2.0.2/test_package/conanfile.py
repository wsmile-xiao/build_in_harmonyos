#!/usr/bin/env python3
"""Conan test_package for libarc 2.0.2 — real consumer test.

Compiles test_arc.c against the packaged static libarc and runs it on
the native OHOS target. test_arc performs 5 check groups (version,
archive-type detection, wildmat matching, compress/decompress
round-trip, end-to-end tar entry read), each printing one "CHECK-OK:"
line. The test() method counts those lines for the
HMBS_TEST_PACKAGE_RESULT machine-evidence marker (exit-0-alone is not
proof: 5 CHECK-OK lines are required for a pass).

Upstream evidence: libarc 2.0.2 ships no automated test harness (no
test dirs, no check/test targets, no TEST/TEST_F/ctest wiring; audit
in MANIFEST.yml), so this re-emits HMBS_UPSTREAM_TEST_RESULT with
status=no_tests on every run.
"""

import glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import copy

# test_arc.c performs exactly 5 check groups, each printing one
# "CHECK-OK: <name>" line on success.
CONSUMER_CHECK_COUNT = 5

_SDK_LLVM_BIN_GLOB = "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin"


def _resolve_cc(conf_value):
    # Same verify-first resolution as the main recipe: the conf path
    # may dangle in sandboxed workers, so only use it when executable.
    candidates = (
        [conf_value, os.environ.get("CC"),
         shutil.which("clang"), shutil.which("cc")]
        + sorted(glob.glob(os.path.join(_SDK_LLVM_BIN_GLOB, "clang")))
        + ["/data/service/hnp/bin/clang"]
    )
    for candidate in candidates:
        if (candidate and os.path.isfile(candidate)
                and os.access(candidate, os.X_OK)):
            return candidate
    raise ConanInvalidConfiguration(
        "libarc test_package: no executable C compiler found "
        "(conf=%r, PATH=%r)" % (conf_value, os.environ.get("PATH"))
    )


class LibarcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # Copy the C test source into the build folder so it is
        # self-contained. Under `conan test` the build folder may equal
        # the source folder, in which case the file is already present
        # and copy() would refuse it.
        if os.path.normpath(self.source_folder) != os.path.normpath(
            self.build_folder
        ):
            copy(self, "test_arc.c", self.source_folder, self.build_folder)

    def build(self):
        # R33: read the OpenHarmony toolchain from Conan conf, never
        # from shell env (verify-first: conf path may dangle, see
        # _resolve_cc).
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = _resolve_cc(compilers.get("c", "clang"))
        dep = self.dependencies["libarc"]
        include_dir = os.path.join(dep.package_folder, "include")
        lib_dir = os.path.join(dep.package_folder, "lib")
        self.run(
            '"%s" -O2 -I"%s" -L"%s" "%s" -o "%s" -larc'
            % (cc, include_dir, lib_dir,
               os.path.join(self.build_folder, "test_arc.c"),
               os.path.join(self.build_folder, "test_arc")),
            env="conanbuild",
        )

    def _ensure_writable_tmp(self):
        # HMBS injects a task-private writable TMPDIR on the real
        # machine (/tmp may be read-only). Prefer it; fall back to a
        # dir under build_folder so the tar fixture never touches /tmp.
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate and os.path.isdir(candidate):
                tmp = candidate
                break
        else:
            tmp = None
        if not tmp:
            tmp = os.path.join(self.build_folder, "hmbs-tmp")
            os.makedirs(tmp, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        return tmp

    def _emit_upstream_marker(self):
        upstream_marker = {
            "status": "no_tests",
            "framework": "make",
            "command": "make (upstream provides no check/test target)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "libarc 2.0.2 ships no automated test harness: no "
                "test/tests directory, no TEST/TEST_F, no ctest/meson/"
                "pytest wiring, no automake TESTS/check_PROGRAMS and no "
                "make check/test target (Makefile targets are only "
                "all/arccat/clean/install; the #ifdef TEST mains in "
                "url_*.c are manual demo programs, not a suite); "
                "see test_package/MANIFEST.yml upstream_test_audit"
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_marker, ensure_ascii=False)
        )

    def test(self):
        if can_run(self):
            self._ensure_writable_tmp()
            bin_path = os.path.join(self.build_folder, "test_arc")
            proc = subprocess.run(
                [bin_path],
                env=dict(os.environ),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=300,
            )
            output = proc.stdout or ""
            self.output.info(output[-2000:])
            ok_count = output.count("CHECK-OK:")
            marker = {
                "executed": True,
                "passed": proc.returncode == 0
                and ok_count == CONSUMER_CHECK_COUNT,
                "command": bin_path,
                "discovered": CONSUMER_CHECK_COUNT,
                "passedCount": ok_count,
            }
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT="
                + json.dumps(marker, ensure_ascii=False)
            )
            self._emit_upstream_marker()
            if not marker["passed"]:
                raise Exception(
                    "consumer test failed: rc=%s ok=%s/%s"
                    % (proc.returncode, ok_count, CONSUMER_CHECK_COUNT)
                )
            self.output.info("libarc consumer test_package passed")
