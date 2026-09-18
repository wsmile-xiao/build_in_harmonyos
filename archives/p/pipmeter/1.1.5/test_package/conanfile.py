#!/usr/bin/env python3
"""Conan test_package for pipmeter 1.1.5.

Runs the packaged ``pipemeter`` binary via test.sh (4 functional cases:
-V version, byte-exact passthrough, -s progress mode, -f file mode) and
emits HMBS evidence markers for preflight verification.

Upstream ships no automated tests (see test_package/MANIFEST.yml audit),
so the HMBS_UPSTREAM_TEST_RESULT marker is re-emitted here on every run
with status "no_tests" (build() is skipped on cache hits, mirroring the
aldo/0.7.8 precedent).
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException


class PipmeterTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        pipemeter_bin = ""
        try:
            ref_name = self.tested_reference_str.split("/")[0]
            dep = self.dependencies[ref_name]
            cand = os.path.join(dep.package_folder, "bin", "pipemeter")
            if os.path.isfile(cand):
                pipemeter_bin = cand
                self.output.info(f"pipemeter found via package_folder: {cand}")
                try:
                    os.chmod(pipemeter_bin, 0o755)
                except Exception:
                    pass
            else:
                self.output.warning(f"pipemeter not in package_folder {dep.package_folder}")
        except Exception as e:
            self.output.warning(f"could not resolve package_folder: {e}")

        actual_cmd = f"{bash} test.sh"
        if pipemeter_bin and os.path.isfile(pipemeter_bin):
            os.environ["CONAN_PIPMETER_BIN"] = pipemeter_bin
            actual_cmd = f'{bash} test.sh "{pipemeter_bin}"'
        discovered = 4
        passed = 0
        try:
            self.run(actual_cmd, env="conanrun")
            passed = discovered
        except Exception as exc:
            self.output.error(f"test.sh failed: {exc}")
            raise
        finally:
            try:
                tp_marker = {
                    "executed": True,
                    "passed": passed == discovered,
                    "command": actual_cmd,
                    "discovered": discovered,
                    "passedCount": passed,
                }
                tp_msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker, ensure_ascii=False)
                print(tp_msg, flush=True)
                self.output.info(tp_msg)
            except Exception:
                pass
            try:
                upstream = {
                    "status": "no_tests",
                    "framework": "autotools",
                    "command": "make check",
                    "discovered": 0,
                    "executed": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "reason": "pipemeter-1.1.5 audited: Makefile.in defines no check target; testscript.sh is a manual 200M benchmark needing /usr/bin/time and /proc/cpuinfo that mails results to the author, not an automated suite; make -n check has no rule",
                }
                up_msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
                print(up_msg, flush=True)
                self.output.info(up_msg)
            except Exception:
                pass
        if passed != discovered:
            raise ConanException("test_package functional tests failed")
