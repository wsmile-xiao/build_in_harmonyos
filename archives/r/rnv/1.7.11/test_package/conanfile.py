import json
import os

from conan import ConanFile


class RnvTestConan(ConanFile):
    """test_package for rnv 1.7.11 — executable verification.

    rnv ships only command-line binaries (rnv/arx/rvp/xsdck; the static
    librnv1.a/librnv2.a are noinst convenience libraries upstream never
    installs), so there is no public library API to link against. Instead
    we verify real binary behaviour with test.sh (4 checks, see
    MANIFEST.yml): version output, grammar check, positive validation and
    negative validation (the last one also proves the harness can catch
    failures instead of silently passing).
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS preflight worker: /data/service/hnp/bin/bash is not
        # executable inside the sandbox (`/bin/sh: bash: inaccessible
        # or not found`, Error 127 — this recipe's own preflight log;
        # the profile may also export a poisoned CONFIG_SHELL pointing
        # at that bash, so it must NOT be trusted here). Upstream
        # rnvtest ran fine under /bin/sh on the same worker, so /bin/sh
        # CAN execute ELF binaries here; run test.sh with POSIX sh
        # (HMBS-guaranteed SHELL, else plain `sh`) via an absolute
        # source path so cwd independence holds. test.sh is POSIX-sh
        # compatible (no bashisms). Precedent: 3d-ascii-viewer-c hardcodes
        # `sh "<source_folder>/script"`.
        shell = os.environ.get("SHELL", "sh") or "sh"
        script = os.path.join(self.source_folder, "test.sh")
        command = '\"%s\" \"%s\"' % (shell, script)
        # hmbs hard gate: the marker must carry the real test_package
        # counts (4 executable checks in test.sh, per MANIFEST.yml).
        result = {"executed": True, "passed": False, "command": command,
                  "discovered": 4, "passedCount": 0}
        try:
            self.run(command, env="conanrun")
        except Exception:
            self.output.info("HMBS_TEST_PACKAGE_RESULT="
                             + json.dumps(result))
            raise
        result["passed"] = True
        result["passedCount"] = 4
        self.output.info("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(result))
