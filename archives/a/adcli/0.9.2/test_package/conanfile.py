import json
import os

from conan import ConanFile


class AdcliTestConan(ConanFile):
    """test_package for adcli 0.9.2 — executable verification.

    adcli ships only the `adcli` command-line binary (the internal
    libadcli.la is a noinst convenience library that upstream does not
    install), so there is no public library API to link against.  Instead
    we verify real binary behaviour:
      - `adcli --help`      prints usage, exits 0
      - `adcli bogus-cmd`   rejects an unknown command, exits 2
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution (same as the acpid recipe).
        # Do NOT trust CONFIG_SHELL here: the preflight wrapper exports
        # CONFIG_SHELL=/bin/sh, which would silently defeat the wrap (the
        # last preflight log showed `RUN: /bin/sh test.sh`).  Prefer the
        # known-good bash from the build toolchain, which libtool itself
        # uses during `make install`.
        bash = "/data/service/hnp/bin/bash"
        if not os.path.exists(bash):
            bash = os.environ.get("CONFIG_SHELL", "sh")
        command = f"{bash} test.sh"
        # hmbs hard gate: the marker must carry the real test_package counts
        # (2 executable checks in test.sh, per MANIFEST.yml).
        result = {"executed": True, "passed": False, "command": command,
                  "discovered": 2, "passedCount": 0}
        try:
            self.run(command, env="conanrun")
        except Exception:
            self.output.info("HMBS_TEST_PACKAGE_RESULT="
                             + json.dumps(result, ensure_ascii=False))
            raise
        result["passed"] = True
        result["passedCount"] = 2
        self.output.info("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(result, ensure_ascii=False))
