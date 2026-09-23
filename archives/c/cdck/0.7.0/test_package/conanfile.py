#!/usr/bin/env python3
"""Consumer test for the packaged cdck executable.

cdck reads real CD/DVD hardware via linux/cdrom.h ioctls; no optical drive
exists in the OHOS build/CI sandbox, so the test exercises the hardware-free
paths (-V version, -h help) plus the fast-failing bad-device path, all of
which run the real binary end to end (R34).

Both HMBS hard-gate markers are emitted in the finally block, so cache-hit
runs (where build() is skipped) stay verifiable: the test_package marker
carries the real executed counts, and the upstream marker re-states the
audited no_tests evidence.
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class CdckTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "test.sh"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.warning("Cannot run cdck in this environment")
            return
        ref_name = self.tested_reference_str.split("/")[0]
        cdck_bin = os.path.join(
            self.dependencies[ref_name].package_folder, "bin", "cdck"
        )
        try:
            os.chmod(cdck_bin, 0o755)
        except OSError:
            pass
        script = os.path.join(self.source_folder, "test.sh")
        # HMBS injects SHELL=/bin/sh; never default to the stale
        # /data/service/hnp/bin/bash (removed from the true-machine image;
        # configure re-exec proved it "inaccessible or not found"). Prefer
        # SHELL, accept CONFIG_SHELL only when it exists on disk.
        shell = os.environ.get("SHELL") or "/bin/sh"
        cfg_shell = os.environ.get("CONFIG_SHELL")
        if not os.environ.get("SHELL") and cfg_shell and os.path.isfile(cfg_shell):
            shell = cfg_shell
        if not os.path.isfile(shell):
            shell = shutil.which("sh") or "/bin/sh"
        actual_cmd = '"%s" "%s" "%s"' % (shell, script, cdck_bin)
        discovered = 4
        passed = 0
        try:
            self.run(actual_cmd, env="conanrun")
            passed = discovered
        except Exception as exc:
            self.output.error("test.sh failed: %s" % exc)
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
                    "reason": "cdck-0.7.0 audited: no tests/ or test/ directory in the tarball; "
                              "Makefile.am files define only SUBDIRS/bin_PROGRAMS/lib_LTLIBRARIES "
                              "with no TESTS, check_PROGRAMS or check target; make check is the "
                              "automake default empty target executing zero cases",
                }
                up_msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
                print(up_msg, flush=True)
                self.output.info(up_msg)
            except Exception:
                pass
        if passed != discovered:
            raise ConanException("test_package shell cases failed")
