#!/usr/bin/env python3
"""Conan test_package — cronolog 1.6.2-rpk.

cronolog is a command-line tool, so the L1 test runs the real binary (R34):
- `cronolog -V` reports a version
- a real pipe-through write with `-o` (once-only) lands byte-identical
- a date-templated write auto-creates subdirectories with identical content.

NOTE: cronolog exits 3 on stdin EOF — that is its normal termination, so
test.sh masks that code (see comments there); any other non-zero is a failure.
"""
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException


class CronologTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _resolve_shell(self):
        # The CI profile buildenv sets CONFIG_SHELL=/data/service/hnp/bin/bash,
        # which is "inaccessible or not found" in some HMBS preflight
        # containers; HMBS instead injects a working SHELL=/bin/sh. Probe
        # candidates on target (existence alone is not enough) and use the
        # first that actually executes. test.sh is pipefail-tolerant so both
        # bash and /bin/sh can run it (E325, numen/hf-mount precedent).
        candidates = [
            os.environ.get("CONFIG_SHELL", ""),
            os.environ.get("SHELL", ""),
            shutil.which("bash") or "",
            "/data/service/hnp/bin/bash",
            "/bin/sh",
            "sh",
        ]
        seen = set()
        for cand in candidates:
            if not cand or cand in seen:
                continue
            seen.add(cand)
            if os.path.isfile(cand):
                try:
                    self.run(f'"{cand}" -c "exit 0"')
                    self.output.info(f"[cronolog test] using shell: {cand}")
                    return cand
                except Exception:
                    continue
            elif cand in ("sh", "bash"):
                try:
                    self.run(f'{cand} -c "exit 0"')
                    self.output.info(f"[cronolog test] using shell: {cand}")
                    return cand
                except Exception:
                    continue
        return "/bin/sh"

    def test(self):
        # Resolve to an actually-executable shell; the stale profile HNP bash
        # path fails exec in HMBS preflight with mksh's
        # "inaccessible or not found".
        bash = self._resolve_shell()
        # Do NOT rely on conanrun PATH for the binary: this vintage package
        # installs sbin_PROGRAMS (normalised to bin/ in package(), but the
        # preflight 2026-09-10 evidence shows conanrun PATH without any
        # conan-home entry -> `cronolog not found on PATH`). Resolve the
        # absolute binary path from the dependency package_folder (bin first,
        # sbin fallback) and hand it to test.sh via CRONOLOG_BIN.
        dep = self.dependencies["cronolog"]
        pkg = dep.package_folder
        self.output.info(f"[cronolog test] package_folder: {pkg}")
        try:
            self.output.info(f"[cronolog test] package bin: {os.listdir(os.path.join(pkg, 'bin'))}")
        except Exception as exc:
            self.output.info(f"[cronolog test] package bin list failed: {exc}")
        try:
            self.output.info(f"[cronolog test] package sbin: {os.listdir(os.path.join(pkg, 'sbin'))}")
        except Exception as exc:
            self.output.info(f"[cronolog test] package sbin list failed: {exc}")
        candidates = [
            os.path.join(pkg, "bin", "cronolog"),
            os.path.join(pkg, "sbin", "cronolog"),
        ]
        cronolog_bin = next((c for c in candidates if os.path.isfile(c)), None)
        if cronolog_bin is None:
            raise ConanException(
                f"cronolog binary not found in package_folder (tried {candidates})"
            )
        self.output.info(f"[cronolog test] using binary: {cronolog_bin}")
        # Upstream harness (noinst_PROGRAMS=cronotest) is staged to bin/ by
        # package() explicitly because `make install` never installs it.
        test_candidates = [
            os.path.join(pkg, "bin", "cronotest"),
            os.path.join(pkg, "sbin", "cronotest"),
        ]
        cronotest_bin = next((c for c in test_candidates if os.path.isfile(c)), None)
        self.output.info(f"[cronolog test] upstream harness: {cronotest_bin}")
        # test.sh runs 3 real assertions against the packaged binary:
        #   1. `cronolog -V` reports the cronolog version
        #   2. `... | cronolog -o <file>` writes byte-identical content (cmp)
        #   3. `... | cronolog <date-template>` auto-creates subdirs (cmp)
        discovered = 3
        passed = 0
        try:
            self.run(f'CRONOLOG_BIN="{cronolog_bin}" "{bash}" test.sh', env="conanrun")
            passed = discovered
        except Exception as exc:
            self.output.error(f"test.sh failed: {exc}")

        # HMBS machine-evidence markers, printed on the Conan output stream
        # (same channel as lzop 1.04, which passed the full gate).
        # test_package count = the 3 real smoke assertions.
        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": f'CRONOLOG_BIN="{cronolog_bin}" "{bash}" test.sh',
            "discovered": discovered,
            "passedCount": passed,
        }
        print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(tp_result)}")

        # Upstream cronolog 1.6.2 ships exactly one executable test harness:
        # src/cronotest.c (noinst_PROGRAMS, usage `cronotest [OPTIONS]
        # template count` — fully non-interactive, deterministic with -s).
        # The testsuite/ dir itself is empty (README: "not yet written"), so
        # this single harness run IS the 1/1 upstream suite. Run it for real
        # on target and report passed/failed from its actual output.
        ut_discovered, ut_executed, ut_passed, ut_failed = 1, 0, 0, 0
        ut_status = "failed"
        ut_command = ""
        if cronotest_bin is None:
            self.output.error(
                f"upstream harness cronotest not found (tried {test_candidates})"
            )
            ut_failed = 1
            ut_command = "cronotest (missing from package bin/)"
        else:
            # Fixed start time makes the run deterministic; %Y/%m/%d template
            # exercises DAILY periodicity over 3 periods. No -D flag: pure
            # computation, no filesystem side effects, no timezone dependence
            # beyond the harness's own localtime rendering.
            # NOTE: parse_time() only accepts month NAMES (%b, e.g. Jan),
            # never numeric months -- numeric start time fails with
            # invalid start time (preflight 2026-09-15). LC_ALL=C pins %b.
            ut_command = (
                f'LC_ALL=C "{cronotest_bin}" -s "01 Jan 2024 00:00:00" '
                f'"logs/%Y/%m/%d/app.log" 3'
            )
            out_file = os.path.join(
                self.build_folder or os.getcwd(), "cronotest-output.txt"
            )
            try:
                self.run(f'{ut_command} > "{out_file}" 2>&1', env="conanrun")
                with open(out_file, encoding="utf-8", errors="replace") as f:
                    ut_output = f.read()
            except Exception as exc:
                ut_output = ""
                self.output.error(f"cronotest run failed: {exc}")
                try:
                    with open(out_file, encoding="utf-8", errors="replace") as f:
                        ut_output = f.read()
                except Exception:
                    pass
            for line in ut_output.splitlines()[:20]:
                self.output.info(f"[cronolog upstream] {line}")
            # Falsifiability: require the harness's real computed content —
            # non-empty output, the rotation-period header, all 3 period
            # lines, and the deterministic 2024 filename expansion. An empty
            # file-vs-empty-file style silent pass cannot satisfy this.
            ut_executed = 1
            if (
                ut_output.strip()
                and "Rotation period" in ut_output
                and "Period 1" in ut_output
                and "Period 3" in ut_output
                and "2024" in ut_output
            ):
                ut_passed = 1
                ut_status = "passed"
                self.output.info("[cronolog upstream] cronotest 1/1 passed")
            else:
                ut_failed = 1
                ut_status = "failed"
                self.output.error(
                    "[cronolog upstream] cronotest output verification failed"
                )
        ut_result = {
            "status": ut_status,
            "framework": "autotools",
            "command": ut_command,
            "discovered": ut_discovered,
            "executed": ut_executed,
            "passed": ut_passed,
            "failed": ut_failed,
            "skipped": 0,
        }
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(ut_result)}")

        if passed != discovered:
            raise ConanException("test_package smoke tests failed")
        if ut_status != "passed":
            raise ConanException("upstream cronotest harness failed")
