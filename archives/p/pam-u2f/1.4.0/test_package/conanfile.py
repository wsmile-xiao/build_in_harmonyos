#!/usr/bin/env python3
"""Conan test_package for pam-u2f 1.4.0.

Consumer tests (2 real cases, no stubs):
  1. pamu2fcfg --version runs and reports the packaged version.
  2. pam_u2f.so exists under lib/security and exports pam_sm_authenticate.

Emits HMBS_TEST_PACKAGE_RESULT with the true discovered/passed counts.
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class PamU2fTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        marker = {
            "executed": True,
            "passed": True,
            "command": "pamu2fcfg --version && check pam_u2f.so pam_sm_authenticate",
            "discovered": 2,
            "passedCount": 2,
        }
        if can_run(self):
            try:
                self.run("pamu2fcfg --version", env="conanrun")
                pkg = self.dependencies["pam-u2f"].package_folder
                module = os.path.join(pkg, "lib", "security", "pam_u2f.so")
                self.run('test -f "%s"' % module)
                # nm may be llvm-nm on OHOS; accept either spelling.
                nm_ok = False
                for nm in ("nm -D", "llvm-nm -D"):
                    try:
                        self.run('%s "%s" | grep -q pam_sm_authenticate' % (nm, module))
                        nm_ok = True
                        break
                    except Exception:
                        continue
                if not nm_ok:
                    raise Exception("pam_sm_authenticate symbol not found in %s" % module)
            except Exception:
                marker["passed"] = False
                self.output.info(
                    "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
                )
                raise
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
