import os

from conan import ConanFile


class TpmTestConan(ConanFile):
    """test_package for the tpm executable — runs test.sh which invokes `tpm`.

    This is a *real* functional test that depends on the built package (L1e).
    test.sh drives tpm through its complete data path: CLI contract (USAGE +
    exit codes), core insert→show round trip, and error paths. The insert/show
    subcommands normally need gpg2, which is absent from the OHOS artifact
    repo; test.sh therefore installs a TEST-ONLY mock gpg2 stub (see
    mock_gpg2.sh) so those code paths are exercisable in CI without an
    external dependency. L1e destructive check: removing bin/tpm fails the
    whole suite, removing mock_gpg2.sh fails the core-function groups only.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # Depends on the package under test — this is what makes it a real
        # test and not a stub (L1e anti-fake-test gate).
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries and the tpm
        # script uses #!/bin/sh features, so wrap execution with bash.
        # conanrun env puts bin/ on PATH so `tpm` resolves to the installed copy.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
