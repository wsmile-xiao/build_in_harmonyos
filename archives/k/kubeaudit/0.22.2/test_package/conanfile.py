#!/usr/bin/env python3
"""Conan test_package for kubeaudit 0.22.2.

Runs test.sh (5 universal offline checks plus 2 OHOS-specific checks against
the packaged binary) and emits the HMBS_TEST_PACKAGE_RESULT marker.

OHOS-specific additions (adaptation-point coverage, not upstream reuse):
  - the packaged Go ELF carries the mandatory OHOS signature section
    (.codesign / .note.ohos) added by binary-sign-tool in build();
  - the CGO_ENABLED=0 binary is statically linked (no PT_INTERP, no
    DT_NEEDED), i.e. free of glibc/musl dynamic coupling on OHOS.
"""

import json
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class KubeauditTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["kubeaudit"].package_folder
        bin_path = os.path.join(package_folder, "bin", "kubeaudit")
        assert os.path.isfile(bin_path), "kubeaudit binary not found: %s" % bin_path
        with open(bin_path, "rb") as handle:
            assert handle.read(4) == b"\x7fELF", "kubeaudit is not an ELF binary"

        is_ohos = str(self.settings.os) == "OHOS"
        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "bash"
            cmd = '%s "%s" "%s"' % (shell, test_script, bin_path)
            if is_ohos:
                cmd += " --ohos"
            self.run(cmd, env="conanrun")

            marker = {
                "executed": True,
                "passed": True,
                "command": "bash test.sh <bin/kubeaudit>" + (" --ohos" if is_ohos else ""),
                "discovered": 7 if is_ohos else 5,
                "passedCount": 7 if is_ohos else 5,
            }
            line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker)
            print(line, flush=True)
            self.output.info(line)
        else:
            self.output.info("kubeaudit binary exists and has ELF magic: %s" % bin_path)
