#!/usr/bin/env python3
"""Conan test_package for libee — L1 consumer test (R34: calls real API).

Builds test_libee.c with a direct clang invocation against the packaged
headers/libs (same convention as the merged libestr 0.1.11 test_package,
avoiding CMake find_library issues on HMDFS) and runs it. The program
performs exactly 6 CHECK-OK assertions; a zero exit status proves all of
them, and the HMBS_TEST_PACKAGE_RESULT marker carries that count.

Upstream evidence: the main recipe build() persists res/hmbs_upstream.json
in the package, re-emitted here on every run (cache-hit rounds skip the
main build, the gate still needs the marker).
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


# test_libee.c performs exactly 6 CHECK-OK assertions (see MANIFEST.yml).
CONSUMER_CHECK_COUNT = 6


def _probe_executable_local(runner, output, path):
    # Same on-target probe as the main recipe: only a real `--version`
    # run proves the compiler is executable here (cronolog precedent).
    import os as _os
    if not path or not _os.path.isfile(path):
        return False
    try:
        runner(f'"{path}" --version')
        return True
    except Exception as exc:
        try:
            output.warning(f"[libee-test] probe failed for {path}: {exc}")
        except Exception:
            pass
        return False


class LibeeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def _resolve_cc(self):
        # R33: toolchain first, PATH fallback only when the configured
        # absolute CC cannot be executed on target (main-build failure was
        # `/data/service/hnp/bin/clang: inaccessible or not found`, 127).
        try:
            ce = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            ce = {}
        cands = []
        configured = ce.get("c") or os.environ.get("CC", "")
        if configured and configured not in cands:
            cands.append(configured)
        for name in ("clang", "cc", "gcc"):
            found = shutil.which(name)
            if found and found not in cands:
                cands.append(found)
        for c in cands:
            if _probe_executable_local(self.run, self.output, c):
                self.output.info(f"[libee-test] using C compiler: {c}")
                return c
        self.output.warning(
            "[libee-test] no probed compiler; falling back to clang"
        )
        return "clang"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        libee = self.dependencies["libee"]
        libestr = self.dependencies["libestr"]
        inc_ee = os.path.join(libee.package_folder, "include")
        lib_ee = os.path.join(libee.package_folder, "lib")
        inc_es = os.path.join(libestr.package_folder, "include")
        lib_es = os.path.join(libestr.package_folder, "lib")

        cc = self._resolve_cc()
        # Compile and link the consumer test program
        self.run(
            f'"{cc}" -fPIC -O2 -I"{inc_ee}" -I"{inc_es}" test_libee.c '
            f'-o test_libee -L"{lib_ee}" -L"{lib_es}" -lee -lestr -lm'
        )

    def test(self):
        if can_run(self):
            discovered = CONSUMER_CHECK_COUNT
            passed = 0
            try:
                # Exit 0 proves all 6 CHECK-OK assertions (any failure
                # aborts the program with exit 1 and a CHECK-FAIL line).
                self.run("./test_libee", env="conanrun")
                passed = discovered
            except Exception as exc:
                self.output.error(f"test_libee failed: {exc}")
                passed = 0
            tp_result = {
                "executed": True,
                "passed": passed == discovered,
                "command": "./test_libee",
                "discovered": discovered,
                "passedCount": passed,
            }
            tp_marker = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_result)
            print(tp_marker, flush=True)
            self.output.info(tp_marker)
            self._reemit_upstream()
            if passed != discovered:
                raise ConanException("test_libee failed")

    def _reemit_upstream(self):
        try:
            dep = self.dependencies["libee"]
            cand = os.path.join(dep.package_folder, "res", "hmbs_upstream.json")
            if os.path.isfile(cand):
                with open(cand, "r", encoding="utf-8") as handle:
                    up = json.load(handle)
                up_marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
                    up, ensure_ascii=False
                )
                print(up_marker, flush=True)
                self.output.info(up_marker)
            else:
                self.output.warning(
                    "hmbs_upstream.json absent from package res/; "
                    "upstream marker left to the main build (cache-miss rounds)"
                )
        except Exception as exc:
            raise ConanException(f"upstream re-emit failed: {exc}")
